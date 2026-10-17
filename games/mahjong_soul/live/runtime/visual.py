"""Conservative 1080p recognition using reviewed tile-face samples.

Only decodes the RGB, filter-zero PNGs produced by WindowsRecorder. Unknown
skins, selected/animated tiles and ambiguous matches remain unsupported.
"""
import base64
from collections import Counter
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


class TileVision:
    MAX_DISTANCE = 6.0
    MIN_MARGIN = 4.0

    def __init__(self, bank=None):
        path = Path(bank) if bank is not None else Path(__file__).with_name("visual_samples.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != 1 or data.get("client_size") != [1920,1080]:
            raise ValueError("Unsupported visual sample bank")
        self.tiles = [(entry["tile"],base64.b64decode(entry["sample"],validate=True)) for entry in data["tiles"]]
        self.skip = base64.b64decode(data["skip"],validate=True)
        if not self.tiles or any(len(value)!=648 for _,value in self.tiles) or len(self.skip)!=648:
            raise ValueError("Invalid visual samples")

    def classify(self, value):
        scores = {}
        for tile, reference in self.tiles:
            scores[tile] = min(scores.get(tile,float("inf")), distance(value,reference))
        ranked = sorted(scores, key=scores.get)
        if len(ranked)<2 or scores[ranked[0]] > self.MAX_DISTANCE or scores[ranked[1]]-scores[ranked[0]] < self.MIN_MARGIN:
            raise ValueError("Unknown or ambiguous visible tile")
        return ranked[0]

    def hand(self, png, profile, expected):
        if profile["client_size"] != [1920,1080]: raise ValueError("Automatic input supports 1080p only")
        rgb = decode_frame(png)
        samples = [sample(rgb, round(x*1919), round(y*1079)) for x,y in profile["slots"]]
        tiles = [self.classify(value) for value in samples]
        if Counter(tiles) != Counter(expected): raise ValueError("Visible hand differs from reader")
        return tiles, samples

    def skip_visible(self, png, profile):
        x,y = profile["skip"]
        value = sample(decode_frame(png),round(x*1919),round(y*1079),220,110)
        if distance(value,self.skip)>self.MAX_DISTANCE: raise ValueError("Skip button is not visually verified")
        return value
