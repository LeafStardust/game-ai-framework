"""Track only event-proven situational Yaku; reconnects do not invent history."""

class ScoringContext:
    def __init__(self,seat):
        self.seat=seat;self.known=False;self.double=[False]*4;self.ippatsu=[False]*4
        self.pending_kan=None;self.last_rinshan=False;self.win={};self.interrupted=False;self.first_discard=True

    def observe(self,name,data,discards,melds,wall,round_meta,hand):
        seat=data.get("seat",0)
        if name=="ActionNewRound":
            self.__init__(self.seat);self.known=True
            self.win={"tenhou":len(hand)==14 and self.seat==round_meta.get("ju")}
            return
        self.win={}
        if not self.known or self.seat not in range(4) or type(seat) is not int or seat not in range(4):return
        called=name in ("ActionChiPengGang","ActionAnGangAddGang","ActionBaBei")
        if called:
            prior_ippatsu=self.ippatsu[self.seat]
            self.interrupted=True
            self.ippatsu=[False]*4
            if name=="ActionAnGangAddGang" or name=="ActionChiPengGang" and data.get("type")==2:self.pending_kan=seat
            if name=="ActionAnGangAddGang" and seat!=self.seat:self.win={"chankan":True,"ippatsu":prior_ippatsu,"double_riichi":self.double[self.seat]}
        if name=="ActionDealTile":
            self.last_rinshan=self.pending_kan==seat;self.pending_kan=None
            if seat==self.seat:
                first=not discards[seat] and not any(melds) and not self.interrupted
                self.win={"rinshan":self.last_rinshan,"haitei":data.get("left_tile_count",wall)==0 and not self.last_rinshan,
                          "chiihou":first and seat!=round_meta.get("ju"),"ippatsu":self.ippatsu[seat],
                          "double_riichi":self.double[seat]}
        elif name=="ActionDiscardTile":
            if seat==self.seat:self.first_discard=False
            if data.get("is_liqi"):
                self.double[seat]=not discards[seat] and not any(melds) and not self.interrupted
                self.ippatsu[seat]=True
            elif self.ippatsu[seat]:self.ippatsu[seat]=False
            if seat!=self.seat:
                self.win={"houtei":wall==0,"ippatsu":self.ippatsu[self.seat],
                          "double_riichi":self.double[self.seat]}

    def snapshot(self):
        seat=self.seat;valid=type(seat) is int and seat in range(4)
        return {"history_complete":self.known,"win":dict(self.win),
                "double_riichi_available":self.known and self.first_discard and not self.interrupted,
                "double_riichi":self.double[seat] if valid else False,
                "ippatsu":self.ippatsu[seat] if valid else False}
