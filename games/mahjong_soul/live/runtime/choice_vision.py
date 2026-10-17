"""Find upright tile faces in the call panel and bind visible choices by tiles.

No server ordering or hand-array ordering is used for screen coordinates.
Unrecognized faces, missing choices, duplicate matches and animations refuse
input. The caller rechecks a second frame and the unchanged live board.
"""
from collections import Counter, deque
from statistics import median
from games.mahjong_soul.live.runtime.call_selection import offer
from games.mahjong_soul.live.runtime.kan import tile_kind


def face_boxes(rgb):
    # Only the choice-panel strip; standing hands and the action label row
    # cannot be mistaken for selectable tiles.
    left,top,right,bottom,step=400,600,1520,850,2
    width=(right-left)//step;height=(bottom-top)//step
    white=bytearray(width*height)
    for row in range(height):
        for col in range(width):
            i=((top+row*step)*1920+left+col*step)*3
            r,g,b=rgb[i:i+3]
            white[row*width+col]=min(r,g,b)>=175 and max(r,g,b)-min(r,g,b)<=35
    boxes=[]
    for index in range(len(white)):
        if not white[index]:continue
        white[index]=0;queue=deque([index]);xmin=xmax=index%width;ymin=ymax=index//width;count=0
        while queue:
            current=queue.popleft();x=current%width;y=current//width;count+=1
            xmin=min(xmin,x);xmax=max(xmax,x);ymin=min(ymin,y);ymax=max(ymax,y)
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<width and 0<=ny<height:
                    n=ny*width+nx
                    if white[n]:white[n]=0;queue.append(n)
        w=(xmax-xmin+1)*step;h=(ymax-ymin+1)*step
        if 28<=w<=120 and 55<=h<=190 and .42<=w/h<=.95 and count*step*step>=w*h*.45:
            if xmin==0 or xmax==width-1 or ymin==0 or ymax==height-1:
                continue  # Partially clipped panels have uncertain geometry.
            boxes.append((left+xmin*step,top+ymin*step,w,h))
    return sorted(boxes)


def group_faces(faces):
    if not faces:raise ValueError("No complete upright call tiles are visible")
    widths=[f[0][2] for f in faces];heights=[f[0][3] for f in faces]
    w,h=median(widths),median(heights)
    if any(abs(f[0][2]-w)>w*.2 or abs(f[0][3]-h)>h*.2 for f in faces):
        raise ValueError("Call tiles have inconsistent sizes")
    groups=[]
    for face in sorted(faces,key=lambda f:f[0][0]):
        if not groups:groups.append([face]);continue
        previous=groups[-1][-1][0];box=face[0]
        gap=box[0]-(previous[0]+previous[2])
        if gap>max(14,w*.35):groups.append([face])
        elif gap<0 or abs(box[1]-previous[1])>h*.15:
            raise ValueError("Call tiles overlap or are not aligned")
        else:groups[-1].append(face)
    return groups


def choice_matches(tiles, combination, report, action):
    expected=Counter(combination.split("|"));visible=Counter(tiles)
    if visible==expected:return True
    kind=action["kind"]
    if kind in ("chi","pon","open_kan"):
        state=report["state"];river=state["discards"][state["turn"]]
        if river and visible==expected+Counter([river[-1]["tile"]]):return True
    if kind=="closed_kan" and len(tiles)==1:
        # A kan menu can show one representative face. Exact four-copy
        # contribution/red identity is still validated against the real hand.
        return len({tile_kind(t) for t in expected})==1 and tile_kind(tiles[0])==tile_kind(next(iter(expected)))
    if kind=="added_kan" and len(tiles)==1:
        pons=[m for m in report["state"]["melds"][report["state"]["seat"]]
              if m.get("type")==1 and len(m.get("tiles",[]))==3
              and all(tile_kind(t)==tile_kind(next(iter(expected))) for t in m["tiles"])]
        return len(pons)==1 and visible==expected-Counter(pons[0]["tiles"])
    return False


def bind_faces(faces, report, action):
    combinations=offer(report,action)
    groups=group_faces(faces)
    visible=[];points=[];values=[]
    for group in groups:
        tiles=[f[1] for f in group]
        matches=[c for c in combinations if choice_matches(tiles,c,report,action)]
        if len(matches)!=1:raise ValueError("Visible call tiles do not identify exactly one server choice")
        visible.append(matches[0])
        left=min(f[0][0] for f in group);right=max(f[0][0]+f[0][2] for f in group)
        top=min(f[0][1] for f in group);bottom=max(f[0][1]+f[0][3] for f in group)
        points.append([(left+right)/2/1919,(top+bottom)/2/1079])
        values.extend(f[2] for f in group)
    if Counter(visible)!=Counter(combinations) or len(set(visible))!=len(visible):
        raise ValueError("The whole call choice panel is not uniquely visible")
    return {"version":1,"verified":True,"stage":"call_choices","client_size":[1920,1080],
            "operation_types":[o["type"] for o in report["state"]["operations"]["operation_list"]],
            "combinations":visible,"choice_points":points},values
