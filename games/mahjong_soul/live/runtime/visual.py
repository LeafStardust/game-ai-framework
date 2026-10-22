"""Conservative 1080p recognition using reviewed tile-face samples.

Only decodes the RGB, filter-zero PNGs produced by WindowsRecorder. Unknown
skins, selected/animated tiles and ambiguous matches remain unsupported.
"""
import base64
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import struct
import zlib


def decode_frame(png):
    if not isinstance(png, bytes) or png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a recorder PNG")
    offset = 8; compressed = bytearray(); size = None; ended = False
    while offset + 12 <= len(png):
        length = struct.unpack_from(">I", png, offset)[0]
        kind = png[offset+4:offset+8]; data = png[offset+8:offset+8+length]
        end = offset + 12 + length
        if end > len(png) or zlib.crc32(kind+data) != struct.unpack_from(">I", png, end-4)[0]:
            raise ValueError("Corrupt recorder PNG")
        if kind == b"IHDR":
            if size is not None or len(data) != 13: raise ValueError("Invalid PNG header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
            if (width, height) != (1920,1080) or (depth,color,compression,filtering,interlace) != (8,2,0,0,0):
                raise ValueError("Recognition requires a 1920x1080 recorder frame")
            size = width, height
        elif kind == b"IDAT": compressed.extend(data)
        elif kind == b"IEND": ended = True; break
        offset = end
    if not ended or size is None: raise ValueError("Incomplete PNG")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(bytes(compressed), (1920*3+1)*1080+1)
    stride = 1920*3
    if not decoder.eof or len(raw) != (stride+1)*1080 or any(raw[y*(stride+1)] for y in range(1080)):
        raise ValueError("Unsupported recorder PNG scanlines")
    return b"".join(raw[y*(stride+1)+1:(y+1)*(stride+1)] for y in range(1080))


def sample(rgb, x, y, width=68, height=110):
    """Fixed face interior, sampled in RGB to distinguish red fives."""
    left, top = round(x-width/2), round(y-height/2)
    if left < 0 or top < 0 or left+width > 1920 or top+height > 1080:
        raise ValueError("Sample outside client")
    result = bytearray()
    for row in range(18):
        py = top + (2*row+1)*height//36
        for col in range(12):
            px = left + (2*col+1)*width//24
            totals = [0,0,0]
            for dy in (-2,-1,0,1,2):
                for dx in (-2,-1,0,1,2):
                    index = ((py+dy)*1920+px+dx)*3
                    for channel in range(3): totals[channel] += rgb[index+channel]
            result.extend(value//25 for value in totals)
    return bytes(result)


def distance(a,b):
    if len(a) != 648 or len(b) != 648: raise ValueError("Invalid sample dimensions")
    return sum(abs(x-y) for x,y in zip(a,b))/len(a)


# Each RGB byte occupies its own unsigned 16-bit lane. The high bit prevents
# subtraction borrowing between lanes; the low byte contains the exact |a-b|.
# This replaces thousands of Python per-channel loops with integer operations.
_SAMPLE_BYTES=648
_LANE_HIGH=int.from_bytes(b"\0\x80"*_SAMPLE_BYTES,"little")
_LANE_LOW=int.from_bytes(b"\xff\0"*_SAMPLE_BYTES,"little")


def _pack_sample(value):
    if len(value)!=_SAMPLE_BYTES:raise ValueError("Invalid sample dimensions")
    lanes=bytearray(_SAMPLE_BYTES*2);lanes[::2]=value
    return int.from_bytes(lanes,"little")


def _packed_distance(a,b):
    delta=(a|_LANE_HIGH)-b
    positive=((delta&_LANE_HIGH)>>15)*65535
    absolute=((delta&positive)|(((b|_LANE_HIGH)-a)&~positive))&_LANE_LOW
    return sum(absolute.to_bytes(_SAMPLE_BYTES*2,"little")[::2])/_SAMPLE_BYTES


class TileVision:
    MAX_DISTANCE = 10.0
    MIN_MARGIN = 4.0

    def __init__(self, bank=None):
        path = Path(bank) if bank is not None else Path(__file__).with_name("visual_samples.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != 1 or data.get("client_size") != [1920,1080]:
            raise ValueError("Unsupported visual sample bank")
        self.tiles = [(entry["tile"],base64.b64decode(entry["sample"],validate=True)) for entry in data["tiles"]]
        calls = json.loads(Path(__file__).with_name("call_samples.json").read_text(encoding="utf-8"))
        if calls.get("version") != 1 or calls.get("client_size") != [1920,1080]:
            raise ValueError("Unsupported call sample bank")
        self._packed_tiles=tuple((tile,_pack_sample(value)) for tile,value in self.tiles)
        self._tile_scores=lru_cache(maxsize=2048)(self._compute_tile_scores)
        self._shape_tiles=tuple(("5"+tile[1:] if tile.startswith("0") else tile,
                                 bytes(min(value[i:i+3]) for i in range(0,len(value),3)))
                                for tile,value in self.tiles)
        self.calls = {kind:base64.b64decode(entry["sample"],validate=True)
                      for kind,entry in calls["buttons"].items()}
        if not {"chi","pon"} <= set(self.calls) <= {"chi","pon","kan","extract_north"} or any(len(v)!=648 for v in self.calls.values()):
            raise ValueError("Invalid call button samples")
        self.call_variants={kind:[base64.b64decode(v,validate=True) for v in entry.get("alternates",[])]
                            for kind,entry in calls["buttons"].items()}
        if any(len(v)!=648 for entries in self.call_variants.values() for v in entries):
            raise ValueError("Invalid call button variant samples")
        declarations=json.loads(Path(__file__).with_name("declaration_samples.json").read_text(encoding="utf-8"))
        if declarations.get("version")!=1 or declarations.get("client_size")!=[1920,1080]:
            raise ValueError("Unsupported declaration sample bank")
        self.declarations={kind:[base64.b64decode(entry["sample"],validate=True) for entry in entries]
                           for kind,entries in declarations["buttons"].items()}
        if set(self.declarations)!={"riichi","ron","tsumo"} or any(not values or any(len(v)!=648 for v in values) for values in self.declarations.values()):
            raise ValueError("Invalid declaration button samples")
        self.skip = base64.b64decode(data["skip"],validate=True)
        if not self.tiles or any(len(value)!=648 for _,value in self.tiles) or len(self.skip)!=648:
            raise ValueError("Invalid visual samples")

    def _compute_tile_scores(self,value):
        query=_pack_sample(value);scores={}
        for tile,reference in self._packed_tiles:
            scores[tile]=min(scores.get(tile,float("inf")),_packed_distance(query,reference))
        return tuple(scores.items())

    def scores(self, value):
        return sorted(({"tile":tile,"distance":score} for tile,score in self._tile_scores(value)),key=lambda x:x["distance"])

    def classify(self, value):
        scores=dict(self._tile_scores(value))
        ranked = sorted(scores, key=scores.get)
        if len(ranked)<2 or scores[ranked[0]] > self.MAX_DISTANCE or scores[ranked[1]]-scores[ranked[0]] < self.MIN_MARGIN:
            # Red 5 Sou shares the five-bamboo glyph; require its shape and red ink.
            shape=lambda data:bytes(min(data[i:i+3]) for i in range(0,len(data),3))
            query=shape(value);shape_scores={}
            for tile,reference_shape in self._shape_tiles:
                error=sum(abs(a-b) for a,b in zip(query,reference_shape))/len(query)
                shape_scores[tile]=min(shape_scores.get(tile,999),error)
            order=sorted(shape_scores,key=shape_scores.get)
            ink=[value[i:i+3] for i in range(0,len(value),3) if max(value[i:i+3])-min(value[i:i+3])>40 and min(value[i:i+3])<170]
            red=sum(r>1.35*g and r>1.25*b for r,g,b in ink)
            if (order[0]=="5s" and shape_scores["5s"]<=6 and shape_scores[order[1]]-shape_scores["5s"]>=3
                    and len(ink)>=12 and red/len(ink)>=.8):return "0s"
            detail=", ".join(f"{tile}:{scores[tile]:.1f}" for tile in ranked[:2])
            raise ValueError("Unknown or ambiguous visible tile ("+detail+")")
        return ranked[0]

    def align_tile(self,rgb,x,y,original):
        """Try only a two-pixel sampling correction, with unchanged confidence.

        Every successful correction must agree on the exact tile label. The
        reader's expected tiles are never used to choose an identity.
        """
        matches=[]
        for dx,dy in ((0,-2),(0,2),(-2,0),(2,0),(-2,-2),(2,-2),(-2,2),(2,2)):
            value=sample(rgb,x+dx,y+dy)
            try:tile=self.classify(value)
            except ValueError:continue
            matches.append((tile,value,(dx,dy)))
        if not matches:raise ValueError(original)
        if len({m[0] for m in matches})!=1:
            raise ValueError("Small alignment corrections disagree on the exact tile")
        return matches[0]

    def hand(self, png, profile, expected):
        if profile["client_size"] != [1920,1080]: raise ValueError("Automatic input supports 1080p only")
        rgb = decode_frame(png)
        samples = [sample(rgb, round(x*1919), round(y*1079)) for x,y in profile["slots"]]
        tiles=[];self.last_diagnostics={"slots":[]}
        for index,value in enumerate(samples):
            alignment=(0,0)
            try:tile=self.classify(value)
            except ValueError as original:
                x,y=profile["slots"][index]
                try:
                    tile,value,alignment=self.align_tile(rgb,round(x*1919),round(y*1079),str(original))
                    samples[index]=value
                except ValueError as error:
                    # Kuikae restrictions dim forbidden tiles after Chi/Pon.
                    # Normalize only when the independently read glyph agrees
                    # with an explicit server restriction; never guess a tile.
                    background=sorted(value)[int(len(value)*.95)]
                    forbidden=profile.get("forbidden_tiles",[])
                    try:
                        if not forbidden or not 100<=background<185:raise ValueError(str(error))
                        normalized=bytes(min(255,round(v*222/background)) for v in value)
                        tile=self.classify(normalized)
                        kind="5"+tile[1:] if tile.startswith("0") else tile
                        if kind not in {"5"+t[1:] if t.startswith("0") else t for t in forbidden}:
                            raise ValueError("Dimmed tile is not forbidden by the server")
                    except ValueError as dim_error:
                        self.last_diagnostics["slots"].append({"slot":index,"nearest":self.scores(value)[:3],"error":str(dim_error)})
                        raise ValueError(f"Slot {index}: {dim_error}") from dim_error
            tiles.append(tile);self.last_diagnostics["slots"].append({"slot":index,"tile":tile,"sampling_offset":list(alignment)})
        if Counter(tiles) != Counter(expected): raise ValueError("Visible hand differs from reader")
        return tiles, samples

    def skip_visible(self, png, profile):
        x,y = profile["skip"]
        value = sample(decode_frame(png),round(x*1919),round(y*1079),220,110)
        if distance(value,self.skip)>self.MAX_DISTANCE: raise ValueError("Skip button is not visually verified")
        return value


    def riichi_hand(self, png, profile, expected, allowed):
        rgb=decode_frame(png);values=[];tiles=[];bright=[]
        for index,(x,y) in enumerate(profile["slots"]):
            value=sample(rgb,round(x*1919),round(y*1079))
            background=sorted(value)[int(len(value)*.95)]
            if background<100:raise ValueError("Riichi hand is obscured")
            visible=background>=185
            normalized=value if visible else bytes(min(255,round(v*222/background)) for v in value)
            tile=self.classify(normalized);tiles.append(tile);values.append(value)
            if visible:bright.append(tile)
        if Counter(tiles)!=Counter(expected):raise ValueError("Riichi hand differs from reader")
        visible_allowed=sorted(set(bright))
        kind=lambda tile:"5"+tile[1:] if tile.startswith("0") else tile
        if {kind(tile) for tile in visible_allowed}!={kind(tile) for tile in allowed}:
            raise ValueError("Bright Riichi discards differ from the offer")
        return tiles,values,visible_allowed

    def choices(self,png,report,action):
        from games.mahjong_soul.live.runtime.choice_vision import face_boxes,bind_faces
        rgb=decode_frame(png);faces=[]
        self.last_diagnostics={"phase":"call_choices","faces":[]}
        for box in face_boxes(rgb):
            x,y,w,h=box
            # Choice faces have different border insets from standing hand
            # tiles. Fit their glyph interior to the reviewed face samples.
            value=sample(rgb,round(x+w/2),round(y+h/2)-2,round(w*.76),round(h*.80))
            try:tile=self.classify(value)
            except ValueError as error:
                self.last_diagnostics["faces"].append({"box":box,"nearest":self.scores(value)[:3],"error":str(error)})
                raise ValueError("Call panel tile is unrecognized: "+str(error)) from error
            self.last_diagnostics["faces"].append({"box":box,"tile":tile})
            faces.append((box,tile,value))
        return bind_faces(faces,report,action)

    def button(self,png,kind,point=None):
        """Recognize a Skip label or a server-offered colored declaration button."""
        rgb=decode_frame(png)
        if kind not in ("skip","chi","pon","kan","extract_north","riichi","ron","tsumo"):
            raise ValueError("Unsupported automatic button kind")
        if kind in ("skip","chi","pon","kan","extract_north"):
            if kind=="kan" and kind not in self.calls:
                # Kan coordinates have already been natively calibrated for
                # exact operation sets. Require the actual outlined action
                # label at that point as well; plain board pixels fail closed.
                if point is None:raise ValueError("Kan requires an exact reviewed offer layout")
                x,y=point
                edges=0;bright=0;dark=0
                for py in range(y-55,y+5):
                    for px in range(x-95,x+95):
                        i=(py*1920+px)*3;r,g,b=rgb[i:i+3]
                        if min(r,g,b)>145 and max(r,g,b)>185:
                            bright+=1
                            for dx,dy in ((3,0),(-3,0),(0,3),(0,-3)):
                                j=((py+dy)*1920+px+dx)*3
                                if max(rgb[j:j+3])<100:edges+=1;break
                        if max(r,g,b)<100:dark+=1
                if edges<80 or bright<150 or dark<150:
                    raise ValueError("Reviewed Kan action label is not visible")
                return x,y,sample(rgb,x,y,220,110)
            reference = self.skip if kind=="skip" else self.calls[kind]
            matches=[]
            for x in ((1290,1020,730,750,480) if kind=="extract_north" else (1290,1020,730,750,480)):
                value=sample(rgb,x,835,220,110)
                if min(distance(value,r) for r in [reference]+self.call_variants.get(kind,[]))<=10:matches.append((x,835,value))
            if len(matches)!=1:raise ValueError(f"{kind.replace('_',' ').title()} button not uniquely visible")
            return matches[0]
        matches=[]
        for x in (1290,1020,750,480):
            value=sample(rgb,x,835,220,110)
            score=min(distance(value,reference) for reference in self.declarations[kind])
            other=min(distance(value,reference) for label,entries in self.declarations.items()
                      if label!=kind for reference in entries)
            if score<=10 and other-score>=4:matches.append((x,835,value))
        if len(matches)!=1:raise ValueError(f"{kind.replace('_',' ').title()} button not uniquely visible")
        if point is not None and abs(matches[0][0]-point[0])>60:
            raise ValueError("Declaration button moved outside its calibration")
        return matches[0]
