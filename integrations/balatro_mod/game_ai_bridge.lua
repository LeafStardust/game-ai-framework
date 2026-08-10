--- STEAMODDED HEADER
--- MOD_NAME: Game AI Bridge
--- MOD_ID: game_ai_bridge
--- MOD_AUTHOR: [LeafStardust]
--- MOD_DESCRIPTION: Exports Balatro runtime state for the General Game AI Agent Framework
--- VERSION: 0.1.0
--- LOADER_VERSION_GEQ: 1.0.0

local BRIDGE_DIRECTORY = "game_ai_bridge"
local STATE_FILE = BRIDGE_DIRECTORY .. "/state.json"
local COMMAND_FILE = BRIDGE_DIRECTORY .. "/command.json"
local EXPORT_INTERVAL = 0.10

local sequence = 0
local last_command_sequence = -1
local elapsed = 0

local function card_snapshot(card)
    if not card then return nil end
    local base = card.base or {}
    local ability = card.ability or {}
    local center = card.config and card.config.center or {}
    return {
        id = tostring(card), rank = base.value, suit = base.suit,
        enhancement = center.key,
        edition = card.edition and card.edition.type or nil,
        seal = card.seal, debuff = card.debuff or false,
        facing = card.facing, center_key = center.key,
        ability_name = ability.name, sell_cost = card.sell_cost,
        cost = card.cost,
    }
end

local function area_cards(area)
    local result = {}
    if not area or not area.cards then return result end
    for _, card in ipairs(area.cards) do
        table.insert(result, card_snapshot(card))
    end
    return result
end

local function current_blind()
    if not G.GAME or not G.GAME.blind then return nil end
    local blind = G.GAME.blind
    return {
        name = blind.name, chips = blind.chips,
        disabled = blind.disabled or false,
        boss = blind.boss or false,
    }
end

local function selected_deck_name(game)
    if game.selected_back and game.selected_back.name then
        return game.selected_back.name
    end
    return nil
end

local function state_name(value)
    for name, state in pairs(G.STATES or {}) do
        if state == value then return name end
    end
    return tostring(value)
end

local function build_snapshot()
    local game = G.GAME or {}
    local round_resets = game.round_resets or {}
    local current_round = game.current_round or {}
    sequence = sequence + 1
    return {
        sequence = sequence,
        phase = state_name(G.STATE),
        state_complete = G.STATE_COMPLETE == true,
        payload = {
            game_state = G.STATE,
            money = game.dollars or 0,
            ante = round_resets.ante or 0,
            round = round_resets.blind_ante or 0,
            blind_score = game.chips or 0,
            hands_left = current_round.hands_left or 0,
            discards_left = current_round.discards_left or 0,
            hand_size = G.hand and G.hand.config and G.hand.config.card_limit or 0,
            consumable_slots = G.consumeables and G.consumeables.config and G.consumeables.config.card_limit or 0,
            stake = game.stake,
            deck_name = selected_deck_name(game),
            hand = area_cards(G.hand), play = area_cards(G.play),
            deck = area_cards(G.deck), jokers = area_cards(G.jokers),
            consumables = area_cards(G.consumeables),
            shop_jokers = area_cards(G.shop_jokers),
            shop_vouchers = area_cards(G.shop_vouchers),
            shop_booster = area_cards(G.shop_booster),
            blind = current_blind(),
        },
    }
end

local function export_snapshot()
    if not G or not json or not love or not love.filesystem then return end
    love.filesystem.createDirectory(BRIDGE_DIRECTORY)
    love.filesystem.write(STATE_FILE, json.encode(build_snapshot()))
end

local function clear_hand_highlights()
    if not G.hand or not G.hand.highlighted then return end
    for index = #G.hand.highlighted, 1, -1 do
        G.hand:remove_from_highlighted(G.hand.highlighted[index])
    end
end

local function highlight_cards(ids)
    if not G.hand or not G.hand.cards then return false end
    local wanted = {}
    for _, id in ipairs(ids or {}) do wanted[id] = true end
    clear_hand_highlights()
    local highlighted = 0
    for _, card in ipairs(G.hand.cards) do
        if wanted[tostring(card)] then
            G.hand:add_to_highlighted(card, true)
            highlighted = highlighted + 1
        end
    end
    return highlighted == #(ids or {})
end

local function find_card(area, id)
    if not area or not area.cards then return nil end
    for _, card in ipairs(area.cards) do
        if tostring(card) == id then return card end
    end
    return nil
end

local function find_shop_card(id)
    return find_card(G.shop_jokers, id)
        or find_card(G.shop_vouchers, id)
        or find_card(G.shop_booster, id)
end

local function execute_command(command)
    if not command or not command.action then return false end
    local payload = command.payload or {}

    if command.action == "PLAY_CARDS" then
        if not highlight_cards(payload.cards) then return false end
        G.FUNCS.play_cards_from_highlighted()
        return true
    end

    if command.action == "DISCARD_CARDS" then
        if not highlight_cards(payload.cards) then return false end
        G.FUNCS.discard_cards_from_highlighted()
        return true
    end

    if command.action == "BUY_JOKER"
        or command.action == "BUY_CONSUMABLE"
        or command.action == "BUY_VOUCHER" then
        local card = find_shop_card(payload.target)
        if not card then return false end
        G.FUNCS.buy_from_shop({config = {ref_table = card}})
        return true
    end

    if command.action == "REFRESH_SHOP" then
        G.FUNCS.reroll_shop()
        return true
    end

    if command.action == "END_SHOP" then
        G.FUNCS.toggle_shop()
        return true
    end

    return false
end

local function process_command()
    if not love.filesystem.getInfo(COMMAND_FILE) then return end
    local raw = love.filesystem.read(COMMAND_FILE)
    if not raw then return end
    local ok, command = pcall(json.decode, raw)
    if not ok or not command then return end
    local command_sequence = tonumber(command.sequence) or -1
    if command_sequence <= last_command_sequence then
        love.filesystem.remove(COMMAND_FILE)
        return
    end
    if execute_command(command) then
        last_command_sequence = command_sequence
    end
    love.filesystem.remove(COMMAND_FILE)
end

local game_update_ref = Game.update
function Game:update(dt)
    game_update_ref(self, dt)
    process_command()
    elapsed = elapsed + dt
    if elapsed >= EXPORT_INTERVAL then
        elapsed = 0
        export_snapshot()
    end
end
