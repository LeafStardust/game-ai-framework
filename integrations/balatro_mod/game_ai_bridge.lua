--- STEAMODDED HEADER
--- MOD_NAME: Game AI Bridge
--- MOD_ID: game_ai_bridge
--- MOD_AUTHOR: [LeafStardust]
--- MOD_DESCRIPTION: Exports Balatro runtime state for the General Game AI Agent Framework
--- VERSION: 0.1.0
--- LOADER_VERSION_GEQ: 1.0.0

local BRIDGE_DIRECTORY = "game_ai_bridge"
local STATE_FILE = BRIDGE_DIRECTORY .. "/state.json"
local EXPORT_INTERVAL = 0.10

local sequence = 0
local elapsed = 0

local function card_snapshot(card)
    if not card then
        return nil
    end

    local base = card.base or {}
    local ability = card.ability or {}
    local center = card.config and card.config.center or {}

    return {
        id = tostring(card),
        rank = base.value,
        suit = base.suit,
        enhancement = center.key,
        edition = card.edition and card.edition.type or nil,
        seal = card.seal,
        debuff = card.debuff or false,
        facing = card.facing,
        center_key = center.key,
        ability_name = ability.name,
        sell_cost = card.sell_cost,
        cost = card.cost,
    }
end

local function area_cards(area)
    local result = {}
    if not area or not area.cards then
        return result
    end

    for _, card in ipairs(area.cards) do
        table.insert(result, card_snapshot(card))
    end

    return result
end

local function current_blind()
    if not G.GAME or not G.GAME.blind then
        return nil
    end

    local blind = G.GAME.blind
    return {
        name = blind.name,
        chips = blind.chips,
        disabled = blind.disabled or false,
        boss = blind.boss or false,
    }
end

local function build_snapshot()
    local game = G.GAME or {}
    local round_resets = game.round_resets or {}
    local current_round = game.current_round or {}

    sequence = sequence + 1

    return {
        sequence = sequence,
        phase = tostring(G.STATE),
        state_complete = G.STATE_COMPLETE == true,
        payload = {
            game_state = G.STATE,
            money = game.dollars or 0,
            ante = round_resets.ante or 0,
            round = round_resets.blind_ante or 0,
            hands_left = current_round.hands_left or 0,
            discards_left = current_round.discards_left or 0,
            chips = current_round.current_hand and current_round.current_hand.chips or 0,
            mult = current_round.current_hand and current_round.current_hand.mult or 0,
            hand = area_cards(G.hand),
            play = area_cards(G.play),
            jokers = area_cards(G.jokers),
            consumables = area_cards(G.consumeables),
            shop_jokers = area_cards(G.shop_jokers),
            shop_vouchers = area_cards(G.shop_vouchers),
            shop_booster = area_cards(G.shop_booster),
            deck_count = G.deck and G.deck.cards and #G.deck.cards or 0,
            blind = current_blind(),
        },
    }
end

local function export_snapshot()
    if not G or not json or not love or not love.filesystem then
        return
    end

    love.filesystem.createDirectory(BRIDGE_DIRECTORY)
    love.filesystem.write(
        STATE_FILE,
        json.encode(build_snapshot())
    )
end

local game_update_ref = Game.update
function Game:update(dt)
    game_update_ref(self, dt)

    elapsed = elapsed + dt
    if elapsed >= EXPORT_INTERVAL then
        elapsed = 0
        export_snapshot()
    end
end
