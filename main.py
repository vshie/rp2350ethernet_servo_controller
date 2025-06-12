
from machine import UART, Pin, PWM
import time
import ujson as json
import os

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
    "focus": PWM(Pin(4))
}

for pwm in servo_pins.values():
    pwm.freq(50)

# Persistent storage
def save_pwm_values():
    with open("pwm_values.txt", "w") as f:
        json.dump(pwm_values, f)

def load_pwm_values():
    if "pwm_values.txt" in os.listdir():
        with open("pwm_values.txt", "r") as f:
            return json.load(f)
    return {"tilt": 1500, "zoom": 1500, "focus": 1500}

pwm_values = load_pwm_values()

def set_pwm_us(pwm, us):
    duty_u16 = int(us * 65535 / 20000)
    pwm.duty_u16(duty_u16)

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

def send_response_html():
    html = """HTTP/1.1 200 OK
Content-Type: text/html
Cache-Control: no-cache, no-store, must-revalidate
Connection: close

<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'>
  <title>RadCam RP2350-ETH Controller</title>
  <style>
    .slider-container { margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>RadCam RP2350-ETH Controller</h1>
  %s
<script>
  function link(slider, number) {
    slider.oninput = () => number.value = slider.value;
    number.onchange = () => slider.value = number.value;
    slider.onchange = () => fetch('/set?' + slider.name + '=' + slider.value);
    number.onchange = () => fetch('/set?' + slider.name + '=' + number.value);
  }

  ['tilt','zoom','focus'].forEach(id => {
    const slider = document.getElementById(id);
    const number = document.getElementById(id + '-val');
    link(slider, number);
  });
</script>
</body>
</html>""" % (
        generate_slider_html("Tilt", "tilt") +
        generate_slider_html("Zoom", "zoom") +
        generate_slider_html("Focus", "focus")
    )
    uart.write(html.encode())
    time.sleep(0.2)
    uart.read()

def generate_slider_html(title, name):
    val = pwm_values[name]
    return f"""<div class='slider-container'>
  <label for='{name}'>{title}:</label><br>
  <input type='range' min='1000' max='2000' step='1' value='{val}' name='{name}' id='{name}'>
  <input type='number' id='{name}-val' value='{val}' min='1000' max='2000'> µs
</div>"""

print("Web server active at http://192.168.2.42")

buffer = b""
while True:
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
                    param, val = query.split("=")
                    val = int(val)
                    if param in pwm_values and 1000 <= val <= 2000:
                        pwm_values[param] = val
                        set_pwm_us(servo_pins[param], val)
                        save_pwm_values()
                        print(f"Updated {param} to {val} us")
                except:
                    pass
                send_response_ok()
            elif "GET / " in request:
                send_response_html()

            buffer = b""  # reset buffer after handling a full request

