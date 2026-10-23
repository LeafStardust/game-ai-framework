from games.mahjong_soul.live.runtime.visual import sample


def scalar(rgb,x,y,width=68,height=110):
    left,top=round(x-width/2),round(y-height/2)
    out=bytearray()
    for row in range(18):
        py=top+(2*row+1)*height//36
        for col in range(12):
            px=left+(2*col+1)*width//24
            out.extend(sum(rgb[((py+dy)*1920+px+dx)*3+c]
                           for dy in range(-2,3) for dx in range(-2,3))//25
                       for c in range(3))
    return bytes(out)


def test_optimized_samples_preserve_all_channels_flooring_and_dimensions():
    rgb=bytes(range(256))*(1920*1080*3//256)
    for bounds in [(500,900,68,110),(1000,500,220,110),(300,200,90,40)]:
        assert sample(rgb,*bounds)==scalar(rgb,*bounds)
