
-- Halo server stat pharser by Devieth.

-- Sapp
api_version = "1.10.0.0"
-- Table
Player_Discord_ID = {}
Player_UUID = {}
Player_Stats = {}
Weapon_Meta_IDs = {}
-- API
API_URL = "http://stats.halopc.com/report/script.php?"
-- Lib
json = require "json"
-- FFI
ffi = require("ffi")
ffi.cdef [[
    typedef void http_response;
    http_response *http_get(const char *url, bool async);
    void http_destroy_response(http_response *);
    void http_wait_async(const http_response *);
    bool http_response_is_null(const http_response *);
    bool http_response_received(const http_response *);
    const char *http_read_response(const http_response *);
    uint32_t http_response_length(const http_response *);
	]]

http_client = ffi.load("lua_http_client")


function OnScriptLoad()
	-- Sigs and Addrs
	ce, client_info_size = 0x40, 0xEC
	network_struct = read_dword(sig_scan("F3ABA1????????BA????????C740??????????E8????????668B0D") + 3)
	gametype_base = read_dword(read_dword(sig_scan("A1????????8B480C894D00") + 0x1))

	-- Callbacks
	register_callback(cb['EVENT_GAME_START'], "OnGameStart")
	register_callback(cb['EVENT_GAME_END'], "OnGameEnd")
	register_callback(cb['EVENT_OBJECT_SPAWN'], "OnEventObjectPreSpawn")
	register_callback(cb['EVENT_DAMAGE_APPLICATION'], "OnEventDamageApplication")
	register_callback(cb['EVENT_JOIN'], "OnPlayerJoin")
	--register_callback(cb['EVENT_LEAVE'], "OnPlayerLeave")
	register_callback(cb['EVENT_CHAT'], "OnEventChat")

	-- Get Weapon_Meta_IDs
	get_metas()

	for i = 1,16 do
		if player_present(i) then
			OnPlayerJoin(i)
		end
	end
end

function OnScriptUnload() end

function OnPlayerJoin(PlayerIndex)
	rprint(PlayerIndex, "|nk") -- Ask for UUID & Disord ID
end

function OnPlayerLeave(PlayerIndex)
	Player_UUID[tonumber(PlayerIndex)] = nil
end

function OnEventChat(PlayerIndex, Message, Mode)
	local PlayerIndex, Mode = tonumber(PlayerIndex), tonumber(Mode)
	-- Capture UUID
	if Mode == 7 then
		Player_UUID[PlayerIndex] = Message
	-- Capture Player_Discord_ID
	elseif Mode == 9 then
		Player_Discord_ID[PlayerIndex] = Message
	end
end

function OnGameStart()
	-- Get Weapon_Meta_IDs
	get_metas()
end

function OnGameEnd()
	-- Loop through all 16 players.
	for i = 1,16 do
		-- Make sure they are present in the server.
		if player_present(i) then
			-- Make sure we got their UUID.
			if Player_UUID[i] then
				-- Set up the the talble that contrains all of their personal stats.
				local Player_Data = {}
				local Discord, UUID, Name = Player_Discord_ID[i], Player_UUID[i], get_name(i)
				local player_won = is_winner(i, get_var(i, "$team"))
				Player_Data["discord"] = Discord
				Player_Data["name"] = Name
				Player_Data["mode"] = get_var(i, "$gt")
				Player_Data["team"] = get_var(i, "$team")
				Player_Data["won"] = player_won
				Player_Data["score"] = get_var(i, "$score")
				Player_Data["kills"] = get_var(i, "$kills")
				Player_Data["assists"] = get_var(i, "$assists")
				Player_Data["deaths"] = get_var(i, "$deaths")
				-- Move their stats out of their global table, so not to overwrite it.
				if Player_Stats[UUID] then
					for key, value in pairs(Player_Stats[UUID]) do
						Player_Data[key] = value
					end
				end
				-- Put everything back in their global table.
				Player_Stats[UUID] = Player_Data
			end
		end
	end

	-- Encode the table.
	local json_message = json.encode(Player_Stats)

	-- Send message to stats server
	GetPage(API_URL.."?"..json_message, true)

	-- Cleanup
	Weapon_Meta_IDs = {}
	Player_UUID = {}
	Player_Discord_ID = {}
end

function is_winner(PlayerIndex, Team)
	local red_score, blue_score = 0,0
	-- Get team score for each team.
	for i = 1,16 do
		if player_present(i) then
			if get_var(i, "$team") == "red" then
				red_score = red_score +  tonumber(get_var(i, "$score"))
			else
				blue_score = blue_score + tonumber(get_var(i, "$score"))
			end
		end
	end
	-- Check if its a tie.
	if blue_score ~= red_score then
		-- Check both winning conditions.
		if blue_score > red_score and Team == "blue" then
			return 1
		elseif red_score > blue_score and Team == "red" then
			return 1
		else -- They lost
			return 0
		end
	else
		return -1
	end
end

-- Count shots fired.
function OnEventObjectPreSpawn(PlayerIndex, MetaID, ParentObjectID, ObjectID)
	local PlayerIndex = tonumber(PlayerIndex)
	-- Make sure we are tracking a player not an object.
	if PlayerIndex > 0 then
		-- Check to make sure the server recived their UUID for tracking.
		if Player_UUID[PlayerIndex] ~= nil then
			-- Check to make sure the server grabbed all weapons IDs.
			if Weapon_Meta_IDs[1] then
				-- Loop through all of the collected Weapon_Meta_IDs to find a match.
				for i = 1,#Weapon_Meta_IDs do
					-- If we found a match, stop the loop and do the accuracy counting.
					if MetaID == Weapon_Meta_IDs[i][1] then
						-- Send the player's UUID, Weapon tag name, and mode.
						count_weapon_accuracy(Player_UUID[PlayerIndex], Weapon_Meta_IDs[i][2], 1)
						break
					end
				end
			end
		end
	end
end

-- Count shots hit.
function OnEventDamageApplication(VictimIndex, PlayerIndex, MetaID, Damage, HitString, Backtap)
	local PlayerIndex, VictimIndex = tonumber(PlayerIndex), tonumber(victimIndex)
	if PlayerIndex > 0 then
		if Player_UUID[PlayerIndex] ~= nil then
			if Weapon_Meta_IDs[1] then
				for i = 1,#Weapon_Meta_IDs do
					if MetaID == Weapon_Meta_IDs[i][1] then
						count_weapon_accuracy(Player_UUID[PlayerIndex], Weapon_Meta_IDs[i][2], 2)
						break
					end
				end
			end
		end
	end
end

function create_accuracy_path(UUID, Weapon_Name, Mode)
	local weapon_stats = {}
	-- If they have stats we are need to rebuild them if a new weapon is being used so not
	-- to overwrite the Player_Stats table every time this is called.
	if Player_Stats[UUID] ~= nil then
		for key, value in pairs(Player_Stats[UUID]) do
			weapon_stats[key] = value
		end
	end
	-- Create new stats entry for detected weapon.
	if Mode == 1 then -- Shots (This should ALWAYS come first.)
		weapon_stats[Weapon_Name] = {1,0}
		Player_Stats[UUID] = weapon_stats
	else -- Hits (Just in case HaloCE does a HaloCE.)
		weapon_stats[Weapon_Name] = {0,1}
		Player_Stats[UUID] = weapon_stats
	end
end

function count_weapon_accuracy(UUID, Weapon_Name, Mode)
	-- Check if they have stats.
	if Player_Stats[UUID] ~= nil then
		-- Check if the weapon has stats.
		if Player_Stats[UUID][Weapon_Name] ~= nil then
			-- Count the weapon stats.
			Player_Stats[UUID][Weapon_Name][Mode] = Player_Stats[UUID][Weapon_Name][Mode] + 1
		else
			create_accuracy_path(UUID, Weapon_Name, Mode)
		end
	else
		create_accuracy_path(UUID, Weapon_Name, Mode)
	end
end

function GetPage(URL, Multithreaded)
    local response = http_client.http_get(URL, Multithreaded)
    local returning = nil
    if http_client.http_response_is_null(response) ~= true then
        local response_text_ptr = http_client.http_read_response(response)
        returning = ffi.string(response_text_ptr)
    end
    http_client.http_destroy_response(response)
    return returning
end

function get_metas()	-- Projectile MapIDs
	local tag_table_base = read_dword(0x40440000)
	local tag_table_count = read_word(0x4044000C)
	for i = 0,tag_table_count-1 do
        local tag = tag_table_base + i * 0x20
        local tag_class = string.reverse(string.sub(read_string(tag),1,4))
        if tag_class == "proj" or tag_class == "jpt!" then
			local tag_name = read_string(read_dword(tag + 0x10))
			local t = tokenizestring(tag_name, "\\")
			local MetaID = read_dword(tag + 0xC)
			Weapon_Meta_IDs[#Weapon_Meta_IDs+1] = {MetaID, t[2]}
        end
    end
end

function get_name(PlayerIndex)
	local PlayerIndex = tonumber(PlayerIndex)
	if player_present(PlayerIndex) then
		local m_player = get_player(PlayerIndex)
		local PlayerNameStruct = (network_struct + 0x1AA + ce + read_byte(m_player + 0x67) * 0x20)
		local PlayerName = read_widestring(PlayerNameStruct, 12)
		return tostring(PlayerName)
	end
end

function read_widestring(Address, Size)
    local str = ""
    for i=0,Size-1 do
        if read_byte(Address + i*2) ~= 00 then
            str = str .. string.char(read_byte(Address + i*2))
        end
    end
    if str ~= "" then return str end
    return nil
end

function tokenizestring(inputstr, sep)
	if sep == nil then
		sep = "%s"
	end
	local t={} ; i=1
	for str in string.gmatch(inputstr, "([^"..sep.."]+)") do
		t[i] = str
		i = i + 1
	end
	return t
end
