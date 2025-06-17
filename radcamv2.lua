--- Focus correction script.


-- Usage: change the output controlling focus from CameraFocus to "Script1"
--        but assign CameraFocus to any other "Disabled" channel as we need to read it, as it allows fine-tuning

K_FOCUS = 92
K_ZOOM = 180
K_SCRIPTING1 = 94

local MARGIN_GAIN = 1.05   -- this will allow us to move 5% beyeond closest/furthest points

-- Lookup tables for closest and furthest focus points
local closest_points = {
    {zoom = 900,  focus = 882},
    {zoom = 1100, focus = 1253},
    {zoom = 1300, focus = 1498},
    {zoom = 1500, focus = 1669},
    {zoom = 1700, focus = 1759},
    {zoom = 1900, focus = 1862},
    {zoom = 2100, focus = 1883}
}

local furthest_points = {
    {zoom = 900,  focus = 935},
    {zoom = 1100, focus = 1305},
    {zoom = 1300, focus = 1520},
    {zoom = 1500, focus = 1696},
    {zoom = 1700, focus = 1811},
    {zoom = 1900, focus = 1911},
    {zoom = 2100, focus = 1930}
}

local focus_channel = SRV_Channels:find_channel(92)
local zoom_channel = SRV_Channels:find_channel(180)
local custom1_channel = SRV_Channels:find_channel(10)

-- set zoom to trim levels
SRV_Channels:set_output_pwm(zoom_channel, 1000)
SRV_Channels:set_range(zoom_channel, 1000)
SRV_Channels:set_output_scaled(zoom_channel, 0)

-- Linear interpolation function
local function lerp(x, x1, y1, x2, y2)
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
end

-- Function to interpolate focus value from lookup table
local function interpolate_focus(zoom, points)
    -- Handle edge cases
    if zoom <= points[1].zoom then
        return points[1].focus
    end
    if zoom >= points[#points].zoom then
        return points[#points].focus
    end
    
    -- Find the bracketing points
    for i = 1, #points - 1 do
        if zoom >= points[i].zoom and zoom < points[i + 1].zoom then
            return lerp(zoom, 
                       points[i].zoom, points[i].focus,
                       points[i + 1].zoom, points[i + 1].focus)
        end
    end
    
    return points[#points].focus -- fallback
end

-- Function to calculate focus position based on zoom position
local function calculate_focus()
    local focus = SRV_Channels:get_output_pwm(K_FOCUS)
    local focus_delta = 0.5 + MARGIN_GAIN * (focus - 1500) / 400.0 -- focus_delta is [0,1], assuming default 1100-1900 limits
    local zoom = SRV_Channels:get_output_pwm(K_ZOOM)
    -- Interpolate both closest and furthest focus values
    local closest_focus = interpolate_focus(zoom, closest_points)
    local furthest_focus = interpolate_focus(zoom, furthest_points)
    
    -- Linear interpolation between closest and furthest based on focus_delta
    return math.floor(closest_focus + focus_delta * (furthest_focus - closest_focus))
end

function update()
    local focus_pos = calculate_focus()
    SRV_Channels:set_output_pwm(K_SCRIPTING1, focus_pos)
    return update, 100
end

return update, 100
