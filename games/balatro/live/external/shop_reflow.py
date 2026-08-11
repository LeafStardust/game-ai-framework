from __future__ import annotations

import time
from dataclasses import dataclass

from games.balatro.actions import BUY_CONSUMABLE, BUY_JOKER, BalatroAction
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.state import BalatroState

from .card_locator import CardFaceLocation, locate_card_faces
from .shop_mouse import (
    ExternalShopMouseExecutor,
    ShopClickSequence,
    ShopMouseLayoutError,
    ShopPointerStep,
)
from .viewport import BalatroViewport, NormalizedPoint, NormalizedRect


# Wide enough that an individual shop card is not rejected as an oversized
# component by the generic card-face detector, while stopping above the Buy
# button row. This is deliberately screen geometry only; item identity still
# comes from the public structured shop observation/projected transaction.
DEFAULT_SHOP_MAIN_CARD_REGION = NormalizedRect(0.40, 0.35, 0.42, 0.22)

# Shop cards contain much more saturated artwork than ordinary playing cards.
# These thresholds were selected from live diagnostics because the stricter hand
# defaults missed The Sun entirely, while looser probes began accepting internal
# artwork fragments as separate cards.
DEFAULT_SHOP_CARD_MIN_BRIGHTNESS = 145
DEFAULT_SHOP_CARD_MAX_CHANNEL_SPREAD = 100


class ShopReflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReflowedShopTarget:
    action: BalatroAction
    visible_index: int
    visible_count: int
    card: CardFaceLocation
    sequence: ShopClickSequence


class ShopMainReflowLocator:
    """Retarget a main-shop purchase from fresh visible card geometry.

    Balatro may recenter/reflow remaining shop cards immediately after a purchase
    while save.jkr remains stale. The projected transaction tells us which public
    offers remain; a fresh screenshot tells us where those offers are now.
    """

    MAIN_ACTIONS = {BUY_JOKER, BUY_CONSUMABLE}

    def __init__(
        self,
        executor: ExternalShopMouseExecutor,
        *,
        region: NormalizedRect = DEFAULT_SHOP_MAIN_CARD_REGION,
        min_brightness: int = DEFAULT_SHOP_CARD_MIN_BRIGHTNESS,
        max_channel_spread: int = DEFAULT_SHOP_CARD_MAX_CHANNEL_SPREAD,
    ):
        self.executor = executor
        self.region = region
        self.min_brightness = min_brightness
        self.max_channel_spread = max_channel_spread

    def locate(self, state: BalatroState, action: BalatroAction) -> ReflowedShopTarget:
        if state.phase != "SHOP":
            raise ValueError("shop reflow location requires SHOP phase")
        if action.name not in self.MAIN_ACTIONS:
            raise ValueError(
                f"shop reflow location supports only main-card purchases, got {action.name}"
            )

        offers = self._remaining_main_offers(state)
        target = action.target
        try:
            visible_index = next(
                index for index, offer in enumerate(offers) if offer is target
            )
        except StopIteration as error:
            raise ShopReflowError(
                "reflow purchase target is not present in projected remaining main offers"
            ) from error

        frame = self.executor._capture_focused_frame()
        main_region = BalatroViewport(frame).crop(self.region)
        cards = locate_card_faces(
            main_region,
            min_brightness=self.min_brightness,
            max_channel_spread=self.max_channel_spread,
        )
        if len(cards) != len(offers):
            raise ShopReflowError(
                "fresh shop-card detection/projected-offer count mismatch: "
                f"screen={len(cards)}, projected={len(offers)}"
            )

        card = cards[visible_index]
        sequence = self._retarget_sequence(action, card.center)
        return ReflowedShopTarget(
            action=action,
            visible_index=visible_index,
            visible_count=len(cards),
            card=card,
            sequence=sequence,
        )

    def dispatch(
        self,
        action: BalatroAction,
        state: BalatroState,
        transaction: BufferedShopTransaction,
        *,
        only_step: int | None = None,
    ) -> ReflowedShopTarget:
        transaction.validate(state, action)
        target = self.locate(state, action)
        steps = target.sequence.steps

        if only_step is not None:
            if only_step < 1 or only_step > len(steps):
                raise ValueError(
                    f"dynamic shop pointer step must be between 1 and {len(steps)}"
                )
            steps = (steps[only_step - 1],)

        # locate() already captured a foreground-safe frame, but its viewport is
        # not exposed. The points are normalized to the same current client area;
        # obtain the current window frame only for pixel conversion and keep the
        # usual focus safety in the executor.
        frame = self.executor._capture_focused_frame()
        viewport = BalatroViewport(frame)

        previous_was_click = False
        for step in steps:
            if previous_was_click and self.executor.between_click_delay > 0:
                time.sleep(self.executor.between_click_delay)

            screen_point = viewport.screen_point(step.point)
            if step.op == "move":
                self.executor.mouse.move_screen(screen_point)
            else:
                self.executor.mouse.click_screen(screen_point)

            if step.delay > 0:
                time.sleep(step.delay)
            previous_was_click = step.op == "click"

        if only_step is None:
            transaction.apply(state, action)
        return target

    def _retarget_sequence(
        self,
        action: BalatroAction,
        detected_center: NormalizedPoint,
    ) -> ShopClickSequence:
        baseline = self.executor.layout.sequence_for(action)
        steps = baseline.steps
        if len(steps) < 2:
            raise ShopMouseLayoutError(
                "dynamic main-shop targeting requires a calibrated card step and Buy step"
            )

        anchor = steps[0].point
        retargeted: list[ShopPointerStep] = []
        for step in steps:
            retargeted.append(
                ShopPointerStep(
                    op=step.op,
                    point=NormalizedPoint(
                        detected_center.x + (step.point.x - anchor.x),
                        detected_center.y + (step.point.y - anchor.y),
                    ),
                    delay=step.delay,
                )
            )
        return ShopClickSequence(tuple(retargeted))

    @staticmethod
    def _remaining_main_offers(state: BalatroState) -> list:
        offers = list(state.shop_jokers) + list(state.shop_consumables)

        def order_key(item):
            value = getattr(item, "area_index", None)
            try:
                return (0, int(value))
            except (TypeError, ValueError):
                return (1, 0)

        return sorted(offers, key=order_key)
