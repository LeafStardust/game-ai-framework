"""Playbook-driven 1080p native play with automatic local incident recording."""
import argparse
import hashlib
import subprocess
from dataclasses import replace
import json
import math
from pathlib import Path
import time

from agents.mahjong_soul.game_budget import GameBudget,positive_games
from agents.mahjong_soul.policy import make_policy
from agents.mahjong_soul.auto_policy import AutomaticPolicy
from agents.mahjong_soul.shadow import ShadowFollower, format_suggestion
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import board_token, plan_discard
from games.mahjong_soul.live.runtime.layout import discard_profile, profile_for_size
from games.mahjong_soul.live.runtime.skip import plan_skip
from games.mahjong_soul.live.runtime.north import plan_north
from games.mahjong_soul.live.runtime.call_selection import CODES, CallMenuPlan, plan_call, plan_call_choice
from games.mahjong_soul.live.runtime.riichi import plan_riichi
from games.mahjong_soul.live.runtime.win import plan_win
from games.mahjong_soul.live.runtime.visual import TileVision, distance


class AutoFollower(ShadowFollower):
    def __init__(self, schema, *, controller, recorder, vision, enabled=False,
                 sleep=time.sleep, journal=None, require_ai=False, games=None, **kwargs):
        super().__init__(schema, **kwargs)
        self.controller, self.recorder, self.vision = controller, recorder, vision
        self.enabled, self.sleep = enabled, sleep
        self.retry_expired=True;self.decision_retries=set()
        self.game_budget=GameBudget(games)
        self.require_ai=require_ai
        self.ai_games=set()
        self.journal=journal
        self.last_recorded_frame=float("-inf")
        self.last_status=None
        self.last_passive_token=None
        self.last_choice_token=None
        self.riichi_pending=None
        self.call_pending=None
        self.halted = None
        self.initial_attempts=controller.snapshot()["attempted_steps"]
        self.source = None
        self.candidate = None
        self.candidate_until = None
        self.candidate_started = None
        self.assist_frame = None
        from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
        self.result_buttons=ResultButtons()
        self.last_result_scan=float("-inf")
        from games.mahjong_soul.live.runtime.assist_buttons import AssistButtons
        self.assist_buttons=AssistButtons()
        self.assist_desired={"auto_win":True,"auto_kita":False,"skip_calls":False,"auto_discard":False}

    def _consume(self, row):
        result = super()._consume(row)
        decoded = (result or {}).get("liqi")
        if decoded:
            connection = row["connection"]
            if decoded.get("method")==".lq.FastTest.authGame" and decoded.get("kind")=="response" and row["direction"]=="server":
                data=decoded.get("data",{});report=self.reader.snapshot()
                key=(connection,report.get("game_generation",0))
                verified=(data.get("game_config",{}).get("mode",{}).get("ai") is True
                          and len(data.get("seat_list",[])) in (3,4) and len(data.get("robots",[]))==len(data.get("seat_list",[]))-1
                          and len(data.get("players",[]))==1 and not data.get("error",{}).get("code",0))
                if verified:self.ai_games.add(key)
                else:self.ai_games.discard(key)
                self._record("ai_room_verified",verified=verified,connection=connection,generation=key[1])
            for event in decoded.get("events", []):
                confirmed=self.controller.observe(connection,event,now=self.clock())
                self._record("game_event",connection=connection,event=event)
                if confirmed:self._record("confirmed",connection=connection,event=event,controller=self.controller.snapshot())
            if self.controller.observe_message(connection,decoded,row["direction"]=="client",now=self.clock()):
                self._record("confirmed",connection=connection,method=decoded.get("method"),controller=self.controller.snapshot())
        return result

    def _record(self,kind,**data):
        if self.journal is not None:self.journal.write(kind,**data)

    def _frame(self,geometry,report,phase):
        started=self.clock()
        png=self.recorder.frame(geometry)
        captured=self.clock()
        first_choice=phase=="call_choices" and board_token(report)!=self.last_choice_token
        if png is not None and self.journal is not None and (phase in ("before_input","before_result_input","before_assist_input","before_room_start") or first_choice or self.clock()-self.last_recorded_frame>=2):
            self.journal.frame(png,geometry=geometry,report=report,phase=phase)
            self.last_recorded_frame=self.clock()
            if phase=="call_choices":self.last_choice_token=board_token(report)
        self._record("frame_timing",phase=phase,capture_seconds=max(0,captured-started),
                     recording_seconds=max(0,self.clock()-captured),available=png is not None)
        return png

    def _park(self):
        backend=getattr(self.controller,"backend",None)
        # Production controller exposes its backend; fake backends may omit park.
        if backend is not None and hasattr(backend,"park"):backend.park(1920,1080)

    def _button_profile(self,report,kind,png,base=None):
        if kind=="kan":
            operations=[o["type"] for o in report["state"]["operations"]["operation_list"]]
            names={(4,):"closed-kan-offer-fullscreen.json",(1,4):"closed-kan-offer-fullscreen.json",(3,5):"open-kan-offer.json",(1,6):"added-kan-offer-fullscreen.json"}
            name=names.get(tuple(operations))
            if name is None:raise ValueError("Kan offer has no reviewed button layout")
            path=Path(__file__).resolve().parents[2]/"games/mahjong_soul/live/layouts"/name
            reviewed=profile_for_size(json.loads(path.read_text(encoding="utf-8")),(1920,1080))
            if reviewed["operation_types"]!=operations and not (operations==[4] and reviewed["operation_types"]==[1,4]):
                raise ValueError("Kan layout offer changed")
            point=tuple(round(v*scale) for v,scale in zip(reviewed["kan"],(1919,1079)))
            x,y,value=self.vision.button(png,kind,point=point)
        else:
            x,y,value=self.vision.button(png,kind)
        profile={} if base is None else dict(base)
        profile.update(version=1,verified=True,client_size=[1920,1080],stage="call_offer",
            operation_types=[o["type"] for o in report["state"]["operations"]["operation_list"]])
        profile[kind]=[x/1919,y/1079]
        self._record("visual_button",kind_name=kind,pixel=[x,y],board_token=board_token(report))
        return profile,value

    @staticmethod
    def _button_kind(kind):
        return "kan" if kind in ("closed_kan","open_kan","added_kan") else kind

    def _plan(self,event):
        started=self.clock();success=False
        try:
            result=self._build_plan(event);success=True
            return result
        finally:
            self._record("preflight_timing",action=event.get("action"),
                         elapsed_seconds=max(0,self.clock()-started),successful=success)

    def _build_plan(self, event):
        report = self._current()
        if board_token(report) != event["board_token"]: raise ValueError("Board changed before visual check")
        if self.require_ai and (report.get("game_connection"),report.get("game_generation",0)) not in self.ai_games:
            raise ValueError("A three- or four-player room with only AI opponents has not been verified from capture")
        geometry = self.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"]) != (1920,1080):
            raise ValueError("Foreground Mahjong client must be 1920x1080")
        action = event["action"]
        if action["kind"] == "discard": profile = discard_profile(report,(1920,1080))
        elif action["kind"]=="riichi": profile=discard_profile(report,(1920,1080))
        else: profile=None
        if profile is not None and report.get("last_event",{}).get("name")=="ActionChiPengGang":
            profile["forbidden_tiles"]=[tile for op in report["state"]["operations"]["operation_list"]
                                        if op["type"]==1 for tile in op.get("combination",[])]
        # This cache supplies only the first observation. A distinct fresh
        # second frame and final board/window checks are mandatory below.
        if profile is not None and action["kind"]=="discard":
            retry=self.controller.snapshot();pending=retry.get("pending") or {}
            if (retry.get("retry_eligible") and pending.get("token")==event["board_token"]
                    and pending.get("tile")==action["tile"]):
                matches=[i for i,point in enumerate(profile["slots"])
                         if tuple(point)==(pending.get("x"),pending.get("y"))]
                if len(matches)==1:profile["retry_selected_slot"]=matches[0]
        cached=self.assist_frame;self.assist_frame=None
        if (cached is not None and cached[1]==geometry and cached[2]==event["board_token"]
                and 0<=self.clock()-cached[3]<=.5):
            first=cached[0]
            self._record("preflight_frame_reused",age_seconds=self.clock()-cached[3])
        else:first = self._frame(geometry,report,"preflight")
        if first is None: raise ValueError("Cannot capture Mahjong client")
        if action["kind"] in ("discard","riichi"):
            tiles, samples = self.vision.hand(first,profile,report["state"]["hand"])
            if action["kind"]=="riichi":
                profile,button_sample=self._button_profile(report,"riichi",first,profile)
                samples.append(button_sample)
        else:
            profile,value=self._button_profile(report,self._button_kind(action["kind"]),first)
            if action["kind"]=="extract_north":plan_north(report,profile,now=self.clock())
            elif action["kind"]=="skip":plan_skip(report,profile,now=self.clock())
            elif action["kind"] in CODES:plan_call(report,profile,action,now=self.clock())
            else:plan_win(report,profile,action["kind"],now=self.clock())
            samples=[value]
        self.sleep(.05)
        if self.recorder.geometry() != geometry: raise ValueError("Game window moved during verification")
        second = self._frame(geometry,report,"before_input")
        if second is None: raise ValueError("Cannot recheck Mahjong client")
        if action["kind"] in ("discard","riichi"):
            current_tiles, current_samples = self.vision.hand(second,profile,report["state"]["hand"])
            if current_tiles != tiles: raise ValueError("Visible hand changed")
            if action["kind"]=="riichi":
                new_profile,value=self._button_profile(report,"riichi",second,profile)
                if new_profile["riichi"]!=profile["riichi"]:raise ValueError("Riichi button moved")
                current_samples.append(value)
        else:
            new_profile,value=self._button_profile(report,self._button_kind(action["kind"]),second)
            if new_profile[self._button_kind(action["kind"]) ]!=profile[self._button_kind(action["kind"])]:raise ValueError("Action button moved")
            current_samples=[value]
        if any(distance(a,b)>1 for a,b in zip(samples,current_samples)):
            raise ValueError("Game UI is still moving")
        current = self._current()
        if board_token(current) != event["board_token"]: raise ValueError("Board changed during visual check")
        if self.recorder.geometry() != geometry: raise ValueError("Game window moved after verification")
        if action["kind"] == "discard":
            plan = replace(plan_discard(current,profile,tiles.index(action["tile"]),action["tile"],now=self.clock()),double_click=True)
        elif action["kind"]=="riichi":
            plan=replace(plan_riichi(current,profile,tiles.index(action["tile"]),action["tile"],now=self.clock()),double_click=True)
        elif action["kind"]=="extract_north":plan=plan_north(current,profile,now=self.clock())
        elif action["kind"]=="skip":plan=plan_skip(current,profile,now=self.clock())
        elif action["kind"] in CODES:plan=plan_call(current,profile,action,now=self.clock())
        else:plan=plan_win(current,profile,action["kind"],now=self.clock())
        return plan,current

    def _result_snapshot(self):
        # Results are intentionally idle on the wire. Preserve source and
        # decode-integrity checks without demanding a new gameplay event.
        if self.path is None or self.reader is None:raise ValueError("No capture source for result verification")
        info=self.path.stat()
        if self._select()!=self.path or (info.st_dev,info.st_ino)!=self.identity:
            raise ValueError("Capture changed during result verification")
        report=self._drain()
        if self.fault or self.tail.pending:raise ValueError("Result capture is incomplete")
        return report

    def _passive_frame(self,phase):
        if self.journal is None or self.recorder is None or self.reader is None:return
        if self.clock()-self.last_recorded_frame<2:return
        report=self.reader.snapshot();token=(board_token(report),report.get("connection_open"))
        operations=((report.get("state") or {}).get("operations") or {}).get("operation_list",[])
        ended=(report.get("state") or {}).get("status") in ("round_ended","match_ended")
        if token==self.last_passive_token and not operations and not ended and phase!="halted":return
        geometry=self.recorder.geometry()
        if geometry:
            self._frame(geometry,report,phase)
            self.last_passive_token=token

    def _continue_riichi(self):
        if self.riichi_pending is None:return
        plan,profile=self.riichi_pending
        pending=self.controller.snapshot().get("pending")
        if pending is None:self.riichi_pending=None;return
        phase=self.controller.riichi_phase()
        if phase!="menu_clicked":return
        report=self._current()
        if board_token(report)!=plan.token:raise ValueError("Board changed before Riichi selection")
        geometry=self.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):raise ValueError("Riichi window unavailable")
        first=self._frame(geometry,report,"riichi_menu")
        tiles,values,allowed=self.vision.riichi_hand(first,profile,report["state"]["hand"],plan.allowed_tiles)
        if tiles.index(plan.tile)!=profile["selected_slot"]:raise ValueError("Riichi tile changed slot")
        self.sleep(.1)
        second=self._frame(geometry,report,"before_input")
        tiles2,values2,allowed2=self.vision.riichi_hand(second,profile,report["state"]["hand"],plan.allowed_tiles)
        if tiles2!=tiles or allowed2!=allowed or any(distance(a,b)>1 for a,b in zip(values,values2)):
            raise ValueError("Riichi menu is still moving")
        report=self._current()
        if self.recorder.geometry()!=geometry:raise ValueError("Riichi window moved")
        # Refresh only expiry; the controller verifies original token and coordinates.
        plan=replace(plan,expires=self.clock()+2)
        self._record("riichi_selection",plan=plan,visible_allowed=allowed)
        self.controller.select_riichi_discard(plan,report,allowed,enabled=True,now=self.clock())
        self._park()

    def _continue_call(self):
        if self.call_pending is None:return
        action,token=self.call_pending
        pending=self.controller.snapshot().get("pending")
        if pending is None:self.call_pending=None;return
        report=self._current()
        if board_token(report)!=token:raise ValueError("Board changed before call choice")
        geometry=self.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):raise ValueError("Call window unavailable")
        first=self._frame(geometry,report,"call_choices")
        profile,values=self.vision.choices(first,report,action)
        plan=plan_call_choice(report,profile,action,now=self.clock())
        self.sleep(.1)
        second=self._frame(geometry,report,"before_input")
        current,values2=self.vision.choices(second,report,action)
        if (current!=profile or len(values)!=len(values2)
                or any(distance(a,b)>1 for a,b in zip(values,values2))):
            raise ValueError("Call choice panel is still moving")
        report=self._current()
        if self.recorder.geometry()!=geometry or board_token(report)!=token:raise ValueError("Call board or window moved")
        self._record("call_selection",plan=plan,visible_profile=profile)
        self.controller.select_call_combination(plan,report,enabled=True,now=self.clock())
        self.call_pending=None
        self._park()

    def _recover_assist_input(self):
        if not self.assist_buttons.failed:return False
        try:
            if not self.assist_buttons.recover(self):return False
            report=self.reader.snapshot()
        except (ValueError,OSError):return False
        self.halted=None;self.candidate=None
        # Only re-evaluate a board with no prior gameplay input. Normal attempt
        # tracking and fresh preflight still prevent duplicate submissions.
        step=(report.get("state") or {}).get("step")
        if not self.controller.was_attempted(report,step):self.seen.discard(board_token(report))
        self._record("input_recovered",confirmation="assist_states_resynchronized")
        return True

    def _recover_advanced_input(self):
        snapshot=self.controller.snapshot()
        if snapshot["status"]!="blocked" or not snapshot.get("pending"):return False
        report=self.reader.snapshot()
        previous=self.halted or snapshot["reason"]
        if self.controller.retire_finished(report):
            self.halted=None;self.candidate=None;self.riichi_pending=None;self.call_pending=None
            self._record("input_recovered",reason=previous,confirmation="server_round_ended")
            return True
        try:
            report=self._current()
            pending=snapshot["pending"]
            if board_token(report)==pending["token"]:return False
            from games.mahjong_soul.live.runtime.decision import decision_request
            request=decision_request(report)
            action=next((a for a in request["actions"] if a["kind"]=="discard"),None)
            if action is None:return False
            # _plan performs the normal two-frame hand, foreground, freshness,
            # AI-room and board-token checks, but sends no input.
            _,current=self._plan({"action":action,"board_token":board_token(report)})
            self.controller.recover(current,visually_verified=True)
        except (ValueError,OSError):return False
        self.halted=None;self.candidate=None;self.riichi_pending=None;self.call_pending=None
        self._record("input_recovered",reason=previous,confirmation="newer_board_visually_verified")
        return True

    def _assist_target_allowed(self,report,key,target):
        from agents.mahjong_soul.assist_preferences import assist_preferences
        from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
        state=report.get("state") or {};seat=state.get("seat");riichi=state.get("riichi",[])
        accepted=isinstance(seat,int) and seat<len(riichi) and riichi[seat]=="accepted"
        prefs=assist_preferences({"observation":observation_from_snapshot(report)},{"kind":"discard"},{})
        if key=="auto_discard" and not accepted and (self.assist_buttons.observed.get("auto_win") is not True
                or prefs["auto_kita"] and self.assist_buttons.observed.get("auto_kita") is not True):
            prefs[key]=False
        return prefs[key] is target

    def _between_turn_assists(self):
        if self.reader is None:return None
        report=self.reader.snapshot();state=report.get("state") or {}
        if state.get("status")!="tracking" or state.get("player_count")!=3:return None
        try:
            from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
            from agents.mahjong_soul.assist_preferences import assist_preferences
            prefs=assist_preferences({"observation":observation_from_snapshot(report)},
                                     {"kind":"discard"},{})
            for key in self.assist_desired:self.assist_desired[key]=prefs[key]
            seat=state.get("seat");riichi=state.get("riichi",[])
            accepted=isinstance(seat,int) and seat<len(riichi) and riichi[seat]=="accepted"
            if not accepted and (self.assist_buttons.observed.get("auto_win") is not True
                                 or self.assist_desired["auto_kita"] and self.assist_buttons.observed.get("auto_kita") is not True):
                self.assist_desired["auto_discard"]=False
            return self.assist_buttons.poll(self,self.assist_desired)
        except (ValueError,OSError) as error:
            self._record("assist_unavailable",reason=str(error))
            return None

    def _game_limit(self):
        if self.reader is None:return None
        before=len(self.game_budget.completed)
        self.game_budget.observe(self.reader.snapshot())
        completed=len(self.game_budget.completed)
        if completed!=before:
            self._record("game_completed",completed=completed,limit=self.game_budget.limit)
        if self.game_budget.done:
            self.enabled=False;self.candidate=None;self.halted=None
            return {"kind":"finished","reason":"game_limit_reached",
                    "completed":completed,"limit":self.game_budget.limit}
        return None

    def poll(self):
        self.assist_frame=None
        if self.game_budget.done:return self._game_limit()
        if self.halted:
            if self.path is not None:
                self._drain()
                finished=self._game_limit()
                if finished is not None:return finished
                if not self._recover_assist_input() and not self._recover_advanced_input():
                    self._passive_frame("halted")
                    if self.assist_buttons.failed:
                        return {"kind":"status","reason":"waiting_for_assist_recovery"}
                    snapshot=self.controller.snapshot()
                    if snapshot["status"]=="blocked" and snapshot.get("pending"):
                        return {"kind":"status","reason":"waiting_for_input_recovery","detail":self.halted}
                    return {"kind":"blocked","reason":self.halted}
            else:return {"kind":"blocked","reason":self.halted}
        event = super().poll()
        finished=self._game_limit()
        if finished is not None:return finished
        recommendation_time=self.clock()
        # Action preflight records its own fresh frames. Avoid a third capture
        # immediately before those two verification frames.
        result_view=(self.reader is not None and (self.reader.snapshot().get("state") or {}).get("status")
                     in ("round_ended","match_ended"))
        if event.get("kind")!="suggestion" and self.candidate is None and not (self.enabled and result_view):
            self._passive_frame("observe")
        if self.enabled and self.reader is not None and self.clock()-self.last_result_scan>=.2:
            self.last_result_scan=self.clock()
            try:
                result=self.result_buttons.poll(self)
                if result is not None:return result
            except (ValueError,OSError,subprocess.TimeoutExpired) as error:
                self._record("result_button_unavailable",reason=str(error))
        if self.path is not None:
            source = (self.path,self.identity)
            if self.source is not None and (source != self.source or self.tail.reset) and self.controller.snapshot()["attempted_steps"]>self.initial_attempts:
                self.halted = "Capture source reset; restart after inspecting the game"
                return {"kind":"blocked","reason":self.halted}
            if self.source!=source:self._record("capture_source",path=str(self.path),identity=list(self.identity))
            self.source = source
            snapshot = self.controller.update(self.reader.snapshot(),now=self.clock())
            if snapshot["status"] == "blocked" and snapshot["reason"]==InputController.TIMEOUT:
                if self._recover_advanced_input():
                    # Shadow polling may have just consumed the newer turn's
                    # recommendation. Preserve it so recovery cannot lose it.
                    if event.get("kind")=="suggestion":
                        self.candidate=event;self.candidate_started=recommendation_time;self.candidate_until=self.clock()+8
                        prefs=event.get("analysis",{}).get("client_assists",{})
                        for key in self.assist_desired:
                            if type(prefs.get(key)) is bool:self.assist_desired[key]=prefs[key]
                        self._record("decision",event=event,report=self.reader.snapshot())
                    return {"kind":"status","reason":"input_recovered"}
                pending=snapshot.get("pending") or {}
                # Retry only ordinary discards, once, after the same full visual
                # preflight used for initial input. _current also requires fresh capture.
                if snapshot.get("retry_eligible"):
                    try:
                        retry_event={"action":{"kind":"discard","tile":pending["tile"]},"board_token":pending["token"]}
                        plan,report=self._plan(retry_event)
                        self._record("retry_attempt",action=retry_event["action"],plan=plan)
                        self.controller.retry_discard(plan,report,visually_verified=True,enabled=True,now=self.clock())
                        self._record("retry_delivered",action=retry_event["action"])
                        self._park()
                    except (ValueError,OSError) as error:
                        self._record("retry_withheld",reason=str(error))
                        current=self.controller.snapshot()
                        if current["reason"] not in (None,InputController.TIMEOUT):
                            self.halted=current["reason"]
                return {"kind":"status","reason":"awaiting_late_confirmation"}
            if snapshot["status"] == "blocked":
                self.halted = snapshot["reason"]
                return {"kind":"blocked","reason":self.halted}
            if snapshot["status"] == "awaiting_confirmation":
                try:
                    self._continue_riichi()
                    self._continue_call()
                except (ValueError,OSError) as error:
                    self._record("preflight_failed",reason=str(error),phase="call_menu" if self.call_pending else "riichi_menu",
                                 image=self.journal.last_frame if self.journal else None,visual=getattr(self.vision,"last_diagnostics",None))
                return {"kind":"status","reason":"awaiting_confirmation"}
        if event.get("reason")=="unsupported_lobby":
            self.candidate=None
            return event
        if not self.enabled: return event
        if event.get("kind")=="suggestion":
            prefs=event.get("analysis",{}).get("client_assists",{})
            for key in self.assist_desired:
                if type(prefs.get(key)) is bool:self.assist_desired[key]=prefs[key]
        if event.get("kind") == "suggestion":
            self.candidate = event
            self.candidate_started = recommendation_time
            self.candidate_until = self.clock()+8
            self._record("decision",event=event,report=self.reader.snapshot() if self.reader else None)
            try:self._park()
            except (ValueError,OSError):pass  # Preflight still requires a foreground frame.
        elif self.candidate is not None:
            if board_token(self.reader.snapshot()) != self.candidate["board_token"]:
                self.candidate = None
                return event
            event = self.candidate
        else:
            assist=self._between_turn_assists()
            return assist if assist is not None else event
        if self.reader is not None:
            state=self.reader.snapshot().get("state") or {}
            seat=state.get("seat");riichi=state.get("riichi",[])
            locked=isinstance(seat,int) and seat<len(riichi) and riichi[seat]=="accepted"
            from agents.mahjong_soul.ready_commit import kan_possible
            from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
            keep_kan=kan_possible(observation_from_snapshot(self.reader.snapshot())["board"])
            if locked:self.assist_desired["auto_discard"]=not keep_kan
            elif (self.assist_buttons.observed.get("auto_win") is not True
                  or self.assist_desired["auto_kita"] and self.assist_buttons.observed.get("auto_kita") is not True):self.assist_desired["auto_discard"]=False
            if locked:self.assist_desired["skip_calls"]=not keep_kan
            elif not state.get("hand"):self.assist_desired["skip_calls"]=False
            try:
                assist=self.assist_buttons.poll(self,self.assist_desired,prepare_optional=False)
                if assist is not None:return assist
            except (ValueError,OSError) as error:self._record("assist_unavailable",reason=str(error))
            pending=self.assist_buttons.pending
            optional_off=(pending and pending[0] in ("auto_win","auto_kita") and pending[1] is True
                          and self.assist_buttons.observed.get(pending[0]) is False)
            if pending and not optional_off:return {"kind":"status","reason":"awaiting_assist_confirmation"}
            if self.assist_buttons.observed.get("auto_win") and event.get("action",{}).get("kind") in ("ron","tsumo"):
                return {"kind":"status","reason":"client_auto_win"}
            if self.assist_buttons.observed.get("auto_discard") and self.assist_desired["auto_discard"] and event.get("action",{}).get("kind")=="discard":
                return {"kind":"status","reason":"client_auto_discard"}
        if event["action"]["kind"] not in ("discard","skip","riichi","ron","tsumo","extract_north",*CODES):
            self.candidate = None
            return {**event,"kind":"manual","reason":"North extraction needs a reviewed button calibration" if event["action"]["kind"]=="extract_north" else "Action requires manual input"}
        try:
            plan,report = self._plan(event)
            if self.controller.was_attempted(report,plan.step):
                self.halted="This game step was already attempted, including prior runs; no retry"
                return {"kind":"blocked","reason":self.halted}
            self._record("plan",plan=plan,action=event["action"],capture=str(self.path),attempt_key=InputController._key(report,plan.step))
            self.controller.submit(plan,report,enabled=True,now=self.clock())
            if isinstance(plan,CallMenuPlan):self.call_pending=dict(event["action"]),plan.token
            if event["action"]["kind"]=="riichi":
                profile=discard_profile(report,(1920,1080))
                profile["selected_slot"]=profile["slots"].index([plan.x,plan.y])
                self.riichi_pending=plan,profile
            self._park()
            self._record("submitted",event=event,controller=self.controller.snapshot())
            if self.candidate_started is not None:
                elapsed=max(0,self.clock()-self.candidate_started)
                self._record("input_latency",elapsed_seconds=elapsed,ideal_seconds=1.0,
                             upper_target_seconds=1.5,over_target=elapsed>1.5,
                             action=event["action"],board_token=event["board_token"])
        except (ValueError,OSError) as error:
            if self.controller.snapshot()["status"] != "idle": self.halted = str(error)
            self._record("preflight_failed",reason=str(error),board_token=event["board_token"],
                         action=event["action"],client_assists=dict(self.assist_buttons.observed),
                         image=self.journal.last_frame if self.journal else None,
                         visual=getattr(self.vision,"last_diagnostics",None))
            if not self.halted:
                # Keep retrying gameplay preflight. Optional switches wait
                # for opponent turns; their setup must not consume this turn.
                if self.clock()<self.candidate_until:return {"kind":"status","reason":"waiting_for_stable_visuals"}
                return {**event,"kind":"waiting_visual","reason":str(error)}
            self.candidate = None
            return {**event,"kind":"blocked" if self.halted else "manual","reason":str(error)}
        self.candidate = None
        return {**event,"kind":"submitted","mode":"auto","executable":True}


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games",type=positive_games,help="Stop after X completed matches; omit for unlimited play")
    parser.add_argument("--execute",action="store_true",help="Enable mouse input; AI room testing")
    parser.add_argument("--playstyle",choices=["balanced","atk"],default="atk")
    parser.add_argument("--file",type=Path)
    parser.add_argument("--duration",type=float)
    parser.add_argument("--once",action="store_true")
    parser.add_argument("--resume-current",action="store_true",help="Arm the current board only with matching live capture health")
    parser.add_argument("--recordings",type=Path,default=root/"logs/mahjong_soul/sessions")
    parser.add_argument("--recording-mb",type=int,default=2048)
    args = parser.parse_args()
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration<=0): parser.error("Duration must be positive and finite")
    if args.recording_mb<16:parser.error("Recording limit must be at least 16 MiB")
    recorder = vision = journal = lease = None
    attempted_keys=()
    # Dry mode never initializes Windows input or screen capture.
    if args.execute:
        from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
        from games.mahjong_soul.live.runtime.windows_recording import WindowsRecorder
        from games.mahjong_soul.live.runtime.session import SessionJournal,RecordingMouse,AgentLease,prior_attempts
        lease=AgentLease(root/"logs/mahjong_soul/agent.lock")
        attempted_keys=prior_attempts(args.recordings)
        journal=SessionJournal(args.recordings,max_bytes=args.recording_mb*1024**2)
        recorder = WindowsRecorder(); vision = TileVision(); backend = RecordingMouse(WindowsMouse(),journal)
        paths=["games/mahjong_soul/live/runtime/room_restart.py","games/mahjong_soul/live/runtime/lobby.py","games/mahjong_soul/live/runtime/north.py","games/mahjong_soul/live/runtime/result_buttons.py",
               "games/mahjong_soul/live/runtime/windows_ocr.ps1","games/mahjong_soul/live/runtime/result_samples.json",
               "agents/mahjong_soul/assist_preferences.py","agents/mahjong_soul/assist_lock.py","agents/mahjong_soul/ready_commit.py", "agents/mahjong_soul/north_choice.py","games/mahjong_soul/live/runtime/assist_buttons.py","games/mahjong_soul/playbook/model.py","games/mahjong_soul/playbook/yonma/east_speed.py","games/mahjong_soul/playbook/sanma/east_speed.py",
               "games/mahjong_soul/playbook/sanma/south_attack.py",
               "agents/mahjong_soul/auto_policy.py","agents/mahjong_soul/attack_policy.py",
               "agents/mahjong_soul/discard_completion.py","agents/mahjong_soul/completion_speed.py","agents/mahjong_soul/speed_lookahead.py",
               "agents/mahjong_soul/attack_value.py","agents/mahjong_soul/attack_defense.py",
               "agents/mahjong_soul/attack_routes.py","agents/mahjong_soul/yakuman.py","agents/mahjong_soul/hand_plan.py","agents/mahjong_soul/scoring.py","agents/mahjong_soul/yaku_catalog.py",
               "agents/mahjong_soul/pattern_yaku.py","games/mahjong_soul/live/runtime/scoring_context.py","games/mahjong_soul/playbook/yonma/south_attack.py",
               "games/mahjong_soul/live/runtime/calls.py","games/mahjong_soul/live/runtime/kan.py",
               "games/mahjong_soul/live/runtime/call_selection.py","games/mahjong_soul/live/runtime/choice_vision.py",
               "games/mahjong_soul/live/runtime/call_samples.json","games/mahjong_soul/live/runtime/declaration_samples.json",
               "agents/mahjong_soul/auto.py","agents/mahjong_soul/game_budget.py","agents/mahjong_soul/playbook_policy.py",
               "games/mahjong_soul/live/runtime/visual.py","games/mahjong_soul/live/runtime/visual_samples.json","games/mahjong_soul/live/runtime/overlay_samples.json",
               "games/mahjong_soul/live/runtime/controller.py","games/mahjong_soul/live/runtime/windows_input.py",
               "games/mahjong_soul/live/runtime/riichi.py",
               "games/mahjong_soul/live/runtime/decision.py","games/mahjong_soul/live/runtime/session.py"]
        try:revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
        except (OSError,subprocess.SubprocessError):revision=None
        journal.write("configuration",games=args.games,playstyle=args.playstyle,revision=revision,
                      source_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths})
        print("Recording: "+str(journal.directory),flush=True)
    else: backend = None
    follower = AutoFollower(LiqiSchema.load(root/"liqi-reference.json"),
        file=args.file,directory=root/"logs/mahjong_soul",policy=AutomaticPolicy(make_policy("playbook",args.playstyle)) if args.execute else make_policy("playbook",args.playstyle),
        controller=InputController(backend,attempted_keys=attempted_keys),recorder=recorder,vision=vision,enabled=args.execute,
        journal=journal,bootstrap_current=args.resume_current,require_ai=True,games=args.games)
    print("Automatic play enabled: discard, Skip, Riichi, Ron, Tsumo, Chi, Pon and kan, including visually verified call choices. Ctrl+C stops." if args.execute else "Suggestions only; mouse input disabled.",flush=True)
    start=time.monotonic(); previous=None; recorded_status=None; heartbeat=start
    try:
        while args.duration is None or time.monotonic()-start<args.duration:
            event=follower.poll()
            kind=event.get("kind")
            if event.get("reason")=="unsupported_lobby":
                message=event["message"]
                if message!=previous:print(message,flush=True);previous=message
            if kind in ("suggestion","submitted","manual","blocked","waiting_visual"):
                line=(format_suggestion(event)+(" [sent; awaiting confirmation]" if kind=="submitted" else "") if "action" in event else "Stopped")
                if kind in ("manual","blocked","waiting_visual"): line += ": "+event["reason"]
                identity=(kind,event.get("board_token"),event.get("reason"))
                if identity != previous: print(line,flush=True);previous=identity
            status_identity=(kind,event.get("board_token"),event.get("reason"))
            if journal is not None and status_identity!=recorded_status:
                journal.write(kind,event=event,reason=event.get("reason"))
                recorded_status=status_identity
            if journal is not None and time.monotonic()-heartbeat>=5:
                journal.write("heartbeat",capture=str(follower.path),controller=follower.controller.snapshot(),halted=follower.halted)
                heartbeat=time.monotonic()
            if kind=="finished":
                print(f"Completed {event['completed']} games; automatic play stopped.",flush=True)
                break
            if args.once: break
            time.sleep(.05)
    except KeyboardInterrupt: pass
    except Exception as error:
        follower.halted=str(error)
        if journal is not None:
            try:journal.write("error",reason=str(error),error_type=type(error).__name__)
            except OSError:pass
        print("Agent stopped: "+str(error),flush=True)
    finally:
        follower.result_buttons.close()
        if lease is not None:lease.close()
        if journal is not None:
            try:journal.close("blocked" if follower.halted else "stopped")
            except OSError:journal.stream.close()
    return 1 if follower.halted else 0


if __name__=="__main__": raise SystemExit(main())
