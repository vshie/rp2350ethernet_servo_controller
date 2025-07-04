from machine import UART, Pin, PWM
import time
import ujson as json
import os

# Slew rate limiting configuration
# Time to move from min to max PWM value (in seconds)
SLEW_RATE_TIMES = {
    "tilt": 2.0,    # 2 seconds for tilt
    "zoom": 2.0,    # 2 seconds for zoom  
    "focus": 2.0,   # 2 seconds for focus
    "yaw": 5.0      # 5 seconds for yaw
}

# PWM ranges for each servo
PWM_RANGES = {
    "tilt": (900, 2100),
    "zoom": (935, 1850),
    "focus": (870, 2130),
    "yaw": (900, 2100)
}

# Current target values (what the user wants)
target_values = {}

# Current actual values (what's being output)
actual_values = {}

# Last update time for each servo
last_update_times = {}

# Setup UART
uart = UART(1, baudrate=115200, tx=Pin(20), rx=Pin(21))

# Enter CH9120 config mode
CFG = Pin(18, Pin.OUT, Pin.PULL_UP)
RST = Pin(19, Pin.OUT, Pin.PULL_UP)

print("begin")
RST.value(1)
CFG.value(0)
time.sleep(0.5)

# Exit config mode
uart.write(b'\x57\xab\x0D')
time.sleep(0.1)
uart.write(b'\x57\xab\x0E')
time.sleep(0.1)
uart.write(b'\x57\xab\x5E')
time.sleep(0.1)
CFG.value(1)
time.sleep(0.1)
print("end")

# PWM pins
servo_pins = {
    "tilt": PWM(Pin(2)),
    "zoom": PWM(Pin(3)),
    "focus": PWM(Pin(4)),
    "yaw": PWM(Pin(5))
}

for pwm in servo_pins.values():
    pwm.freq(50)

# Persistent storage
def save_pwm_values():
    with open("pwm_values.txt", "w") as f:
        json.dump(target_values, f)

def load_pwm_values():
    if "pwm_values.txt" in os.listdir():
        with open("pwm_values.txt", "r") as f:
            return json.load(f)
    return {"tilt": 1500, "zoom": 1500, "focus": 1500, "yaw": 1500}

pwm_values = load_pwm_values()

# Initialize target and actual values
for name, val in pwm_values.items():
    target_values[name] = val
    actual_values[name] = val
    last_update_times[name] = time.time()

# Set initial servo positions
for name, val in actual_values.items():
    set_pwm_us(servo_pins[name], val)

def set_pwm_us(pwm, us):
    duty_u16 = int(us * 65535 / 20000)
    pwm.duty_u16(duty_u16)

def calculate_slew_rate_step(servo_name):
    """Calculate the maximum step size for smooth movement"""
    min_val, max_val = PWM_RANGES[servo_name]
    total_range = max_val - min_val
    time_to_traverse = SLEW_RATE_TIMES[servo_name]
    # Assume we want to update at ~50Hz for smooth movement
    updates_per_second = 50
    total_updates = time_to_traverse * updates_per_second
    return max(1, int(total_range / total_updates))

def update_servo_positions():
    """Update actual servo positions based on slew rate limits"""
    current_time = time.time()
    
    for servo_name in servo_pins.keys():
        if target_values[servo_name] != actual_values[servo_name]:
            # Calculate maximum step size for this servo
            max_step = calculate_slew_rate_step(servo_name)
            
            # Calculate time since last update
            time_since_update = current_time - last_update_times[servo_name]
            # Update at 50Hz
            if time_since_update >= 0.02:  # 20ms = 50Hz
                current_val = actual_values[servo_name]
                target_val = target_values[servo_name]
                
                # Move towards target
                if current_val < target_val:
                    new_val = min(current_val + max_step, target_val)
                else:
                    new_val = max(current_val - max_step, target_val)
                
                # Update actual value and output
                actual_values[servo_name] = new_val
                set_pwm_us(servo_pins[servo_name], new_val)
                last_update_times[servo_name] = current_time

# Lookup tables for closest and furthest focus points (from radcamv2.lua)
closest_points = [
    (900,  882),
    (1100, 1253),
    (1300, 1498),
    (1500, 1669),
    (1700, 1759),
    (1900, 1862),
    (2100, 1883)
]

furthest_points = [
    (900,  935),
    (1100, 1305),
    (1300, 1520),
    (1500, 1696),
    (1700, 1811),
    (1900, 1911),
    (2100, 1930)
]

def interpolate(zoom, points):
    # Handle edge cases
    if zoom <= points[0][0]:
        return points[0][1]
    if zoom >= points[-1][0]:
        return points[-1][1]
    
    # Find the bracketing points
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 <= zoom <= x2:
            return int(y1 + (zoom - x1) * (y2 - y1) / (x2 - x1))
    
    return points[-1][1]  # fallback

def calculate_autofocus(zoom, focus):
    margin_gain = 1.05  # Same as MARGIN_GAIN in radcamv2.lua
    focus_delta = 0.5 + margin_gain * (focus - 1500) / 400.0  # Same focus_delta calculation
    closest = interpolate(zoom, closest_points)
    furthest = interpolate(zoom, furthest_points)
    return int(closest + focus_delta * (furthest - closest))

for name, val in pwm_values.items():
    set_pwm_us(servo_pins[name], val)

def send_response_ok():
    body = "OK"
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        "Cache-Control: no-cache, no-store, must-revalidate\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n%s" % (len(body), body)
    )
    uart.write(response.encode())
    time.sleep(0.1)
    uart.read()

def generate_slider_html(title, name, minval, maxval):
    val = target_values[name]  # Use target value for display
    left_label = {"tilt": "Down", "zoom": "Out", "focus": "Closer", "yaw": "Left"}[name]
    right_label = {"tilt": "Up", "zoom": "In", "focus": "Farther", "yaw": "Right"}[name]
    
    # For tilt, reverse the values so Down (left) = high PWM, Up (right) = low PWM
    if name == "tilt":
        display_val = maxval + minval - val  # Reverse the display value
    else:
        display_val = val
        
    return """<div>
  <label>""" + title + """:</label>
  <div>
    <span style="font-style: italic">""" + left_label + """</span>
    <input type='range' min='""" + str(minval) + """' max='""" + str(maxval) + """' step='1' value='""" + str(display_val) + """' name='""" + name + """' id='""" + name + """'>
    <span style="font-style: italic">""" + right_label + """</span>
  </div>
  <input type='number' id='""" + name + """-val' value='""" + str(display_val) + """' min='""" + str(minval) + """' max='""" + str(maxval) + """'> µs
</div>"""

def send_response_html():
    sliders = (
        generate_slider_html("Focus", "focus", 870, 2130) +
        generate_slider_html("Zoom", "zoom", 935, 1850) +
        generate_slider_html("Tilt", "tilt", 900, 2100) +
        generate_slider_html("Yaw", "yaw", 900, 2100)
    )
    
    html = """HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Cache-Control: no-cache, no-store, must-revalidate
Connection: close

<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>RadCam RP2350-ETH Controller</title>
  <style>
    body { margin: 20px; }
    h1 { text-align: center; }
    label { font-weight: bold; display: block; text-align: center; }
    input[type='number'] { text-align: center; width: 100px; }
    div { text-align: center; }
    input[type='range'] { width: 80%; }
    .iframe-container { margin-top: 30px; }
    .url-input { width: 60%; padding: 8px; margin-right: 10px; }
    .refresh-btn { padding: 8px 20px; }
    iframe { width: 100%; height: 1000px; border: 1px solid #ccc; margin-top: 10px; }
    .error-message { color: red; margin-top: 10px; display: none; }
    .loading { display: none; margin-top: 10px; }
  </style>
</head>
<body>
  <h1>RadCam RP2350-ETH Controller</h1>
""" + sliders + """
  <div class="iframe-container">
    <input type="text" id="urlInput" class="url-input" placeholder="Enter URL or IP address" value="192.168.2.10">
    <button onclick="loadIframe()" class="refresh-btn">Load/Refresh</button>
    <div id="loading" class="loading">Loading...</div>
    <div id="errorMessage" class="error-message"></div>
    <iframe id="contentFrame" src="http://192.168.2.10" allow="fullscreen" allowfullscreen sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-top-navigation"></iframe>
  </div>
<script>
  // Store the last manually set focus value
  var lastManualFocus = """ + str(target_values['focus']) + """;

  function updateFocusDisplay(newFocus) {
    var focusSlider = document.getElementById('focus');
    var focusNumber = document.getElementById('focus-val');
    focusSlider.value = newFocus;
    focusNumber.value = newFocus;
  }

  function link(slider, number) {
    slider.oninput = function() { 
      number.value = slider.value;
      if (slider.name === 'zoom') {
        // Use the last manually set focus value for calculations
        fetch('/set?zoom=' + slider.value + '&focus=' + lastManualFocus)
          .then(response => response.text())
          .then(data => {
            // Parse the response to get the new focus value
            var newFocus = parseInt(data);
            if (!isNaN(newFocus)) {
              updateFocusDisplay(newFocus);
            }
          });
      } else if (slider.name === 'focus') {
        // Update the last manually set focus value
        lastManualFocus = slider.value;
        fetch('/set?focus=' + slider.value);
      } else if (slider.name === 'tilt') {
        // Convert display value back to actual PWM value for tilt
        var actualPWM = 2100 + 900 - parseInt(slider.value);
        fetch('/set?tilt=' + actualPWM);
      } else {
        fetch('/set?' + slider.name + '=' + slider.value);
      }
    };
    number.oninput = function() { 
      slider.value = number.value;
      if (slider.name === 'zoom') {
        // Use the last manually set focus value for calculations
        fetch('/set?zoom=' + number.value + '&focus=' + lastManualFocus)
          .then(response => response.text())
          .then(data => {
            // Parse the response to get the new focus value
            var newFocus = parseInt(data);
            if (!isNaN(newFocus)) {
              updateFocusDisplay(newFocus);
            }
          });
      } else if (slider.name === 'focus') {
        // Update the last manually set focus value
        lastManualFocus = number.value;
        fetch('/set?focus=' + number.value);
      } else if (slider.name === 'tilt') {
        // Convert display value back to actual PWM value for tilt
        var actualPWM = 2100 + 900 - parseInt(number.value);
        fetch('/set?tilt=' + actualPWM);
      } else {
        fetch('/set?' + slider.name + '=' + number.value);
      }
    };
  }
  ['focus','zoom','tilt','yaw'].forEach(function(id) {
    var slider = document.getElementById(id);
    var number = document.getElementById(id + '-val');
    link(slider, number);
  });

  function showError(message) {
    var errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('loading').style.display = 'none';
  }

  function loadIframe() {
    var url = document.getElementById('urlInput').value;
    var errorDiv = document.getElementById('errorMessage');
    var loadingDiv = document.getElementById('loading');
    var iframe = document.getElementById('contentFrame');
    
    errorDiv.style.display = 'none';
    loadingDiv.style.display = 'block';
    
    if (url) {
      // Add http:// if no protocol is specified
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'http://' + url;
      }
      
      iframe.src = url;
      loadingDiv.style.display = 'none';
    } else {
      showError('Please enter a URL');
      loadingDiv.style.display = 'none';
    }
  }

  // Allow Enter key to trigger iframe load
  document.getElementById('urlInput').addEventListener('keyup', function(e) {
    if (e.key === 'Enter') {
      loadIframe();
    }
  });

  // Load the default URL when the page loads
  window.onload = function() {
    loadIframe();
  };
</script>
</body>
</html>"""
    uart.write(html.encode())
    time.sleep(0.2)
    uart.read()

print("Web server active at http://192.168.2.42")

buffer = b""
while True:
    # Update servo positions based on slew rate limits
    update_servo_positions()
    
    if uart.any():
        buffer += uart.read(uart.any())
        if b"\r\n\r\n" in buffer:
            print("Decoding buffer:", buffer)
            try:
                request = buffer.decode("utf-8")
            except:
                buffer = b""
                continue
            print("Request received:", request)

            if "GET /set?" in request:
                try:
                    query = request.split("GET /set?")[1].split(" ")[0]
                    # Handle both single parameter and zoom+focus combination
                    if '&' in query:
                        # Handle zoom+focus combination
                        params = query.split('&')
                        zoom_param = params[0].split('=')
                        focus_param = params[1].split('=')
                        if zoom_param[0] == 'zoom' and focus_param[0] == 'focus':
                            zoom_val = int(zoom_param[1])
                            focus_val = int(focus_param[1])
                            target_values['zoom'] = zoom_val  # Set target instead of actual
                            # Calculate and set new focus value
                            new_focus = calculate_autofocus(zoom_val, focus_val)
                            target_values['focus'] = new_focus  # Set target instead of actual
                            # Save target values to persistent storage
                            pwm_values = target_values.copy()
                            save_pwm_values()
                            print(f"Updated zoom target to {zoom_val} us and focus target to {new_focus} us")
                            # Return the new focus value in the response
                            response = str(new_focus)
                            send_response = (
                                "HTTP/1.1 200 OK\r\n"
                                "Content-Type: text/plain\r\n"
                                "Cache-Control: no-cache, no-store, must-revalidate\r\n"
                                "Content-Length: %d\r\n"
                                "Connection: close\r\n"
                                "\r\n%s" % (len(response), response)
                            )
                            uart.write(send_response.encode())
                            time.sleep(0.1)
                            uart.read()
                    else:
                        # Handle single parameter
                        param, val = query.split("=")
                        val = int(val)
                        if param in target_values:
                            target_values[param] = val  # Set target instead of actual
                            # Save target values to persistent storage
                            pwm_values = target_values.copy()
                            save_pwm_values()
                            print(f"Updated {param} target to {val} us")
                            send_response_ok()
                except:
                    pass
                    send_response_ok()
            elif "GET / " in request:
                send_response_html()

            buffer = b""
