-- game-ai-framework first-party Balatro action bridge.
--
-- Loaded directly into Balatro by Lovely. This code intentionally has no
-- Steamodded or BalatroBot dependency. Commands are polled from a tiny local
-- file protocol and executed from love.update on the normal game thread.

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

    -- Toggle only differences instead of calling unhighlight_all(). This keeps
    -- Balatro's own selection restrictions authoritative (important for boss
    -- effects such as forced selections).
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

  local function process_command(command_id, action, payload)
    if action == "PING" then
      write_response(command_id, "OK", "ready")
      return
    end

    if action ~= "PLAY" and action ~= "DISCARD" then
      write_response(
        command_id,
        "ERROR",
        "unsupported action: " .. tostring(action)
      )
      return
    end

    local ok, result, message = pcall(
      execute_hand_action,
      action,
      payload
    )
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
      -- A command-level error is normally reported with its command id. This
      -- catch prevents bridge failures from escaping into Balatro's update loop.
      print(
        "[game-ai-framework bridge] "
          .. sanitize_message(error_message)
      )
    end
  end
end
