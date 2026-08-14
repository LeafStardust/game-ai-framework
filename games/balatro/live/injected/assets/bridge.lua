-- game-ai-framework first-party Balatro action bridge.
--
-- Loaded directly from Balatro's fused LÖVE archive. This code intentionally
-- has no Lovely, Steamodded, or BalatroBot dependency. Commands are polled from
-- a tiny local file protocol and executed from love.update on the normal game
-- thread.

if not GAME_AI_FRAMEWORK_BRIDGE_INSTALLED then
  GAME_AI_FRAMEWORK_BRIDGE_INSTALLED = true

  local appdata = os.getenv("APPDATA")
  local bridge_dir = appdata and (appdata .. "/Balatro/game-ai-framework-bridge") or nil
  local command_path = bridge_dir and (bridge_dir .. "/command.txt") or nil
  local response_path = bridge_dir and (bridge_dir .. "/response.txt") or nil

  local function sanitize_message(value)
    return tostring(value or ""):gsub("[\t\r\n]", " ")
  end

  local function write_response(command_id, status, message)
    if not response_path then
      return
    end

    local temporary = response_path .. ".tmp"
    local file = io.open(temporary, "w")
    if not file then
      return
    end

    file:write(
      tostring(command_id),
      "\t",
      tostring(status),
      "\t",
      sanitize_message(message),
      "\n"
    )
    file:close()
    os.remove(response_path)
    os.rename(temporary, response_path)
  end

  local function read_command()
    if not command_path then
      return nil
    end

    local file = io.open(command_path, "r")
    if not file then
      return nil
    end

    local text = file:read("*a") or ""
    file:close()
    os.remove(command_path)

    local command_id, action, payload =
      text:match("^([^\t\r\n]+)\t([A-Z_]+)\t?([^\r\n]*)")
    if not command_id or not action then
      return "unknown", "INVALID", "malformed command"
    end
    return command_id, action, payload or ""
  end

  local function parse_indices(payload)
    local indices = {}
    local seen = {}

    if payload == "" then
      return indices
    end

    for token in payload:gmatch("[^,]+") do
      local index = tonumber(token)
      if not index or index < 0 or index ~= math.floor(index) then
        return nil, "invalid hand index: " .. tostring(token)
      end
      if seen[index] then
        return nil, "duplicate hand index: " .. tostring(index)
      end
      seen[index] = true
      table.insert(indices, index)
    end

    return indices
  end

  local function parse_single_index(payload)
    if not payload or payload == "" or payload:find(",", 1, true) then
      return nil, "exactly one non-negative index is required"
    end
    local index = tonumber(payload)
    if not index or index < 0 or index ~= math.floor(index) then
      return nil, "invalid action index: " .. tostring(payload)
    end
    return index
  end

  local function parse_consumable_use_payload(payload)
    if not payload or payload == "" then
      return nil, nil, "consumable use requires a held consumable index"
    end

    local slot_payload, target_payload = payload:match("^([^,]+),?(.*)$")
    local slot, slot_error = parse_single_index(slot_payload)
    if slot == nil then
      return nil, nil, slot_error
    end

    local targets, target_error = parse_indices(target_payload or "")
    if not targets then
      return nil, nil, target_error
    end

    return slot, targets
  end

  local function parse_pack_select_payload(payload)
    if not payload or payload == "" then
      return nil, nil, "pack selection requires a pack card index"
    end

    local slot_payload, target_payload = payload:match("^([^,]+),?(.*)$")
    local slot, slot_error = parse_single_index(slot_payload)
    if slot == nil then
      return nil, nil, slot_error
    end

    local targets, target_error = parse_indices(target_payload or "")
    if not targets then
      return nil, nil, target_error
    end

    return slot, targets
  end

  local function achievement_gate_state()
    if not G then
      return "G_UNAVAILABLE"
    end

    local value = G.F_NO_ACHIEVEMENTS
    if value == nil then
      return "UNSET"
    end
    if type(value) == "boolean" then
      return value and "DISABLED" or "ENABLED"
    end
    return "UNEXPECTED:" .. type(value)
  end

  local function restart_run_callback_state()
    if type(G) ~= "table" then
      return "NO_G"
    end
    if type(G.FUNCS) ~= "table" then
      return "NO_FUNCS"
    end
    if type(G.FUNCS.start_run) == "function" then
      return "START_RUN_PRESENT"
    end
    return "MISSING"
  end

  local function bridge_status()
    return "bridge=1;achievement_gate=" .. achievement_gate_state()
      .. ";restart_run_callback=" .. restart_run_callback_state()
  end

  local function highlighted_set()
    local set = {}
    local list = {}
    if G and G.hand and G.hand.highlighted then
      for _, card in ipairs(G.hand.highlighted) do
        set[card] = true
        table.insert(list, card)
      end
    end
    return set, list
  end

  local function clear_hand_selection()
    local _, current = highlighted_set()
    for _, card in ipairs(current) do
      card:click()
    end
    local _, remaining = highlighted_set()
    if #remaining ~= 0 then
      return false, "Balatro rejected clearing highlighted cards"
    end
    return true
  end

  local function select_hand_indices(indices)
    if not G or not G.hand or not G.hand.cards then
      return false, "Balatro hand is unavailable"
    end

    local limit =
      G.hand.config and tonumber(G.hand.config.highlighted_limit) or 5
    if #indices == 0 then
      return false, "at least one hand index is required"
    end
    if #indices > limit then
      return false, "selection exceeds highlighted card limit"
    end

    local desired = {}
    local ordered = {}
    for _, index in ipairs(indices) do
      local card = G.hand.cards[index + 1]
      if not card then
        return false, "invalid hand index: " .. tostring(index)
      end
      desired[card] = true
      table.insert(ordered, card)
    end

    local _, current = highlighted_set()
    for _, card in ipairs(current) do
      if not desired[card] then
        card:click()
      end
    end

    local selected = highlighted_set()
    for _, card in ipairs(ordered) do
      if not selected[card] then
        card:click()
        selected = highlighted_set()
      end
    end

    local final_set, final_list = highlighted_set()
    if #final_list ~= #ordered then
      return false, "Balatro rejected the requested highlighted-card set"
    end
    for _, card in ipairs(ordered) do
      if not final_set[card] then
        return false, "Balatro rejected one or more requested cards"
      end
    end

    return true
  end

  local function action_button(button_id)
    if not G or not G.buttons or not G.buttons.UIRoot or not UIBox then
      return nil
    end
    return UIBox:get_UIE_by_ID(button_id, G.buttons.UIRoot)
  end

  local function execute_hand_action(action, payload)
    if not G or not G.STATES or G.STATE ~= G.STATES.SELECTING_HAND then
      return false, "hand action requires SELECTING_HAND"
    end

    local indices, parse_error = parse_indices(payload)
    if not indices then
      return false, parse_error
    end

    if action == "DISCARD" then
      local round = G.GAME and G.GAME.current_round
      if not round or tonumber(round.discards_left or 0) <= 0 then
        return false, "no discards remaining"
      end
    end

    local selected, selection_error = select_hand_indices(indices)
    if not selected then
      return false, selection_error
    end

    local button_id =
      action == "PLAY" and "play_button" or "discard_button"
    local button = action_button(button_id)
    if not button then
      return false, button_id .. " not found"
    end

    local callback
    if action == "PLAY" then
      callback = G.FUNCS and G.FUNCS.play_cards_from_highlighted
    else
      callback = G.FUNCS and G.FUNCS.discard_cards_from_highlighted
    end
    if type(callback) ~= "function" then
      return false, "Balatro action callback is unavailable"
    end

    local ok, error_message = pcall(callback, button)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_consumable_use(payload)
    if not G or not G.STATES then
      return false, "Balatro state is unavailable"
    end

    local selecting_hand = G.STATE == G.STATES.SELECTING_HAND
    local in_shop = G.STATE == G.STATES.SHOP
    if not selecting_hand and not in_shop then
      return false, "consumable use requires SELECTING_HAND or validated SHOP use"
    end
    if not G.consumeables or not G.consumeables.cards then
      return false, "held consumables are unavailable"
    end

    local consumable_index, target_indices, parse_error =
      parse_consumable_use_payload(payload)
    if consumable_index == nil then
      return false, parse_error
    end

    local card = G.consumeables.cards[consumable_index + 1]
    if not card then
      return false, "held consumable index is out of range"
    end

    if in_shop then
      if #target_indices ~= 0 then
        return false, "SHOP held-consumable use cannot include hand targets"
      end
      local center = card.config and card.config.center
      local key = center and center.key
      if key ~= "c_hermit"
        and key ~= "c_temperance"
        and key ~= "c_wheel_of_fortune" then
        return false, "held consumable is not validated for SHOP use"
      end
    else
      local selected, selection_error
      if #target_indices == 0 then
        selected, selection_error = clear_hand_selection()
      else
        selected, selection_error = select_hand_indices(target_indices)
      end
      if not selected then
        return false, selection_error
      end
    end

    local callback = G.FUNCS and G.FUNCS.use_card
    if type(callback) ~= "function" then
      return false, "use_card callback is unavailable"
    end

    local button = { config = { ref_table = card } }
    local ok, error_message = pcall(callback, button)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function available_money()
    if not G or not G.GAME then
      return nil
    end
    return tonumber(G.GAME.dollars or 0) - tonumber(G.GAME.bankrupt_at or 0)
  end

  local function require_state(state_name)
    if not G or not G.STATES or G.STATE ~= G.STATES[state_name] then
      return false, "action requires " .. tostring(state_name)
    end
    return true
  end

  local function is_pack_state()
    if not G or not G.STATES then
      return false
    end
    local names = {
      "TAROT_PACK",
      "PLANET_PACK",
      "SPECTRAL_PACK",
      "STANDARD_PACK",
      "BUFFOON_PACK",
    }
    for _, name in ipairs(names) do
      local state = G.STATES[name]
      if state ~= nil and G.STATE == state then
        return true
      end
    end
    return false
  end

  local function shop_card(area, index)
    if not area or not area.cards then
      return nil
    end
    return area.cards[index + 1]
  end

  local function affordable(card)
    local money = available_money()
    local cost = card and tonumber(card.cost or 0) or nil
    if money == nil or cost == nil then
      return false, "card cost or available money is unavailable"
    end
    if cost > money then
      return false, "item is not affordable"
    end
    return true
  end

  local function room_for_shop_card(card)
    local set = card and card.ability and card.ability.set
    if set == "Joker" then
      local count = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_count or 0) or 0
      local limit = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_limit or 0) or 0
      if count >= limit then
        return false, "joker slots are full"
      end
    elseif set == "Tarot" or set == "Planet" or set == "Spectral" then
      local count = G.consumeables and G.consumeables.config and tonumber(G.consumeables.config.card_count or 0) or 0
      local limit = G.consumeables and G.consumeables.config and tonumber(G.consumeables.config.card_limit or 0) or 0
      if count >= limit then
        return false, "consumable slots are full"
      end
    end
    return true
  end

  local function execute_cash_out()
    local ready, state_error = require_state("ROUND_EVAL")
    if not ready then
      return false, state_error
    end
    local callback = G.FUNCS and G.FUNCS.cash_out
    if type(callback) ~= "function" then
      return false, "cash_out callback is unavailable"
    end
    local ok, error_message = pcall(callback, { config = {} })
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_next_round()
    local ready, state_error = require_state("SHOP")
    if not ready then
      return false, state_error
    end
    local callback = G.FUNCS and G.FUNCS.toggle_shop
    if type(callback) ~= "function" then
      return false, "toggle_shop callback is unavailable"
    end
    local ok, error_message = pcall(callback, {})
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_select_blind()
    local ready, state_error = require_state("BLIND_SELECT")
    if not ready then
      return false, state_error
    end
    if not G.GAME or not G.GAME.blind_on_deck then
      return false, "current blind on deck is unavailable"
    end
    if not G.blind_select_opts then
      return false, "blind select options are unavailable"
    end

    local current_blind = tostring(G.GAME.blind_on_deck)
    local blind_pane = G.blind_select_opts[string.lower(current_blind)]
    if not blind_pane or type(blind_pane.get_UIE_by_ID) ~= "function" then
      return false, "current blind pane is unavailable"
    end
    local select_button = blind_pane:get_UIE_by_ID("select_blind_button")
    if not select_button then
      return false, "select blind button is unavailable"
    end

    local callback = G.FUNCS and G.FUNCS.select_blind
    if type(callback) ~= "function" then
      return false, "select_blind callback is unavailable"
    end
    local ok, error_message = pcall(callback, select_button)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_reroll_shop()
    local ready, state_error = require_state("SHOP")
    if not ready then
      return false, state_error
    end
    local round = G.GAME and G.GAME.current_round
    local cost = round and tonumber(round.reroll_cost or 0) or 0
    local money = available_money()
    if money == nil then
      return false, "available money is unavailable"
    end
    if cost > 0 and money < cost then
      return false, "not enough dollars to reroll"
    end
    local callback = G.FUNCS and G.FUNCS.reroll_shop
    if type(callback) ~= "function" then
      return false, "reroll_shop callback is unavailable"
    end
    local ok, error_message = pcall(callback, nil)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_shop_purchase(action, payload)
    local ready, state_error = require_state("SHOP")
    if not ready then
      return false, state_error
    end

    local index, parse_error = parse_single_index(payload)
    if index == nil then
      return false, parse_error
    end

    local area
    if action == "BUY_CARD" or action == "BUY_AND_USE_CONSUMABLE" then
      area = G.shop_jokers
    elseif action == "BUY_VOUCHER" then
      area = G.shop_vouchers
    else
      area = G.shop_booster
    end

    local card = shop_card(area, index)
    if not card then
      return false, "shop item index is out of range"
    end

    if action == "BUY_AND_USE_CONSUMABLE" then
      local set = card.ability and card.ability.set
      if set ~= "Tarot" and set ~= "Planet" and set ~= "Spectral" then
        return false, "Buy & Use requires a Tarot, Planet, or Spectral shop item"
      end
    end

    local can_afford, affordability_error = affordable(card)
    if not can_afford then
      return false, affordability_error
    end

    if action == "BUY_CARD" then
      local has_room, room_error = room_for_shop_card(card)
      if not has_room then
        return false, room_error
      end
    end

    local button
    if action == "BUY_AND_USE_CONSUMABLE" then
      local child = card.children and card.children.buy_and_use_button
      local ui_root = child and child.UIRoot
      local config = ui_root and ui_root.config
      if not config
        or config.button ~= "buy_from_shop"
        or config.func ~= "can_buy_and_use" then
        return false, "shop item has no active Buy & Use control"
      end
      button = child.definition
    else
      button = card.children and card.children.buy_button and card.children.buy_button.definition
    end
    if not button then
      return false, "shop item buy button is unavailable"
    end

    local callback
    if action == "BUY_CARD" or action == "BUY_AND_USE_CONSUMABLE" then
      callback = G.FUNCS and G.FUNCS.buy_from_shop
    else
      callback = G.FUNCS and G.FUNCS.use_card
    end
    if type(callback) ~= "function" then
      return false, "shop purchase callback is unavailable"
    end

    local ok, error_message = pcall(callback, button)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_sell_joker(payload)
    local ready, state_error = require_state("SHOP")n    if not ready then
      return false, state_error
    end

    local index, parse_error = parse_single_index(payload)
    if index == nil then
      return false, parse_error
    end
    if not G.jokers or not G.jokers.cards then
      return false, "joker area is unavailable"
    end

    local joker = G.jokers.cards[index + 1]
    if not joker then
      return false, "joker index is out of range"
    end

    local callback = G.FUNCS and G.FUNCS.sell_card
    if type(callback) ~= "function" then
      return false, "sell_card callback is unavailable"
    end

    local ok, error_message = pcall(
      callback,
      { config = { ref_table = joker } }
    )
    if not ok then
      return false, error_message
    end
    return true
  end

  local function pack_card_requires_hand_targets(card)
    local center = card and card.config and card.config.center
    local key = center and center.key
    local config = center and center.config
    if key == "c_aura" then
      return true
    end
    return config and config.max_highlighted ~= nil
  end

  local function execute_pack_select(payload)
    if not is_pack_state() then
      return false, "pack selection requires a native *_PACK state"
    end
    if not G.pack_cards or G.pack_cards.REMOVED or not G.pack_cards.cards then
      return false, "no booster pack is open"
    end

    local index, target_indices, parse_error = parse_pack_select_payload(payload)
    if index == nil then
      return false, parse_error
    end
    local card = G.pack_cards.cards[index + 1]
    if not card then
      return false, "pack card index is out of range"
    end

    local requires_targets = pack_card_requires_hand_targets(card)
    local selected, selection_error
    if requires_targets then
      if #target_indices == 0 then
        return false, "pack card requires hand targets"
      end
      selected, selection_error = select_hand_indices(target_indices)
    else
      if #target_indices ~= 0 then
        return false, "pack card does not accept hand targets"
      end
      selected, selection_error = clear_hand_selection()
    end
    if not selected then
      return false, selection_error
    end

    if card.ability and card.ability.set == "Joker" then
      local count = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_count or 0) or 0
      local limit = G.jokers and G.jokers.config and tonumber(G.jokers.config.card_limit or 0) or 0
      if count >= limit then
        return false, "joker slots are full"
      end
    end

    local callback = G.FUNCS and G.FUNCS.use_card
    if type(callback) ~= "function" then
      return false, "use_card callback is unavailable"
    end
    local button = { config = { ref_table = card } }
    local ok, error_message = pcall(callback, button)
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_pack_skip()
    if not is_pack_state() then
      return false, "pack skip requires a native *_PACK state"
    end
    if not G.pack_cards or G.pack_cards.REMOVED then
      return false, "no booster pack is open"
    end
    local callback = G.FUNCS and G.FUNCS.skip_booster
    if type(callback) ~= "function" then
      return false, "skip_booster callback is unavailable"
    end
    local ok, error_message = pcall(callback, {})
    if not ok then
      return false, error_message
    end
    return true
  end

  local function execute_restart_run()
    if not G or not G.STATES or G.STATE ~= G.STATES.GAME_OVER then
      return false, "run restart requires GAME_OVER"
    end
    if not G.GAME then
      return false, "Balatro run state is unavailable"
    end
    if G.GAME.won then
      return false, "won runs must not be restarted automatically"
    end
    if G.GAME.seeded then
      return false, "automatic restart supports unseeded runs only"
    end
    if G.GAME.challenge then
      return false, "automatic restart does not support challenge runs"
    end
    if not G.STAGES or G.STAGE ~= G.STAGES.RUN then
      return false, "run restart requires RUN stage"
    end
    local stake = tonumber(G.GAME.stake)
    if not stake or stake < 1 or stake ~= math.floor(stake) then
      return false, "current stake is unavailable"
    end
    local callback = G.FUNCS and G.FUNCS.start_setup_run
    if type(callback) ~= "function" then
      return false, "start_setup_run callback is unavailable"
    end
    if type(G.save_settings) ~= "function" then
      return false, "save_settings callback is unavailable"
    end

    local profile = G.PROFILES and G.SETTINGS and G.PROFILES[G.SETTINGS.profile]
    local streak = profile and profile.high_scores and profile.high_scores.current_streak
    if not streak then
      return false, "current streak state is unavailable"
    end

    -- Mirror Balatro's native held-R restart setup for a normal unseeded run.
    streak.amt = 0
    G:save_settings()
    G.SETTINGS.current_setup = "New Run"
    G.GAME.viewed_back = nil
    G.run_setup_seed = false
    G.challenge_tab = nil
    G.forced_seed = nil
    G.setup_seed = nil
    G.forced_stake = stake

    local ok, error_message = pcall(callback)

    -- start_setup_run consumes these synchronously while building the args table;
    -- clear the temporary globals exactly as the native controller path does.
    G.forced_stake = nil
    G.challenge_tab = nil
    G.forced_seed = nil

    if not ok then
      return false, error_message
    end
    return true
  end

  local function process_command(command_id, action, payload)
    if action == "PING" then
      write_response(command_id, "OK", "ready")
      return
    end

    if action == "STATUS" then
      write_response(command_id, "OK", bridge_status())
      return
    end

    local executor
    if action == "PLAY" or action == "DISCARD" then
      executor = function()
        return execute_hand_action(action, payload)
      end
    elseif action == "USE_CONSUMABLE" then
      executor = function()
        return execute_consumable_use(payload)
      end
    elseif action == "CASH_OUT" then
      executor = execute_cash_out
    elseif action == "NEXT_ROUND" then
      executor = execute_next_round
    elseif action == "SELECT_BLIND" then
      executor = execute_select_blind
    elseif action == "REROLL_SHOP" then
      executor = execute_reroll_shop
    elseif action == "BUY_CARD"
      or action == "BUY_AND_USE_CONSUMABLE"
      or action == "BUY_VOUCHER"
      or action == "BUY_BOOSTER" then
      executor = function()
        return execute_shop_purchase(action, payload)
      end
    elseif action == "SELL_JOKER" then
      executor = function()
        return execute_sell_joker(payload)
      end
    elseif action == "PACK_SELECT" then
      executor = function()
        return execute_pack_select(payload)
      end
    elseif action == "PACK_SKIP" then
      executor = execute_pack_skip
    elseif action == "RESTART_RUN" then
      executor = execute_restart_run
    else
      write_response(
        command_id,
        "ERROR",
        "unsupported action: " .. tostring(action)
      )
      return
    end

    local ok, result, message = pcall(executor)
    if not ok then
      write_response(command_id, "ERROR", result)
      return
    end
    if not result then
      write_response(command_id, "ERROR", message)
      return
    end
    write_response(command_id, "OK", "accepted")
  end

  local function poll_bridge()
    local command_id, action, payload = read_command()
    if not command_id then
      return
    end
    process_command(command_id, action, payload)
  end

  local original_love_update = love.update
  love.update = function(dt)
    if original_love_update then
      original_love_update(dt)
    end

    local ok, error_message = pcall(poll_bridge)
    if not ok then
      print(
        "[game-ai-framework bridge] "
          .. sanitize_message(error_message)
      )
    end
  end
end
