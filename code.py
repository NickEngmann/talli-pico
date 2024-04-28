import board
import digitalio
from adafruit_seesaw import seesaw, rotaryio
from adafruit_seesaw import digitalio as DIO
import adafruit_display_text.label
from adafruit_bitmap_font import bitmap_font
import framebufferio
import sharpdisplay
import time
import displayio
import microcontroller


class BatchDisplayUpdate:
    def __init__(self, the_display):
        self.the_display = the_display
        self.auto_refresh = the_display.auto_refresh

    def __enter__(self):
        self.the_display.auto_refresh = False

    def __exit__(self, unused1, unused2, unused3):
        self.the_display.refresh()
        self.the_display.auto_refresh = self.auto_refresh

# Configuration for CS pin (for the OLED display):
CS_PIN = board.D7

# Configuring button and encoder
BUTTON_PIN = board.D3
ENCODER_BUTTON_PIN = 24  # Pin number for the button on the rotary encoder

# SPI and display initialization
displayio.release_displays()
spi = board.SPI()
framebuffer = sharpdisplay.SharpMemoryFramebuffer(spi, CS_PIN, 160, 68)
display = framebufferio.FramebufferDisplay(framebuffer)


def save_number(number):
    microcontroller.nvm[0:4] = number.to_bytes(4, 'little')

def load_number():
    try:
        return int.from_bytes(microcontroller.nvm[0:4], 'little')
    except ValueError:
        return 0

def update_display():
    global last_displayed_number
    with BatchDisplayUpdate(display):
        if locked:
            text_area.text = ""
        else:
            text_area.text = f"{number:03}"
            last_displayed_number = number
        display.root_group = text_group
        print("Display updated. Number:", number, "Locked:", locked)

# Load the font
font = bitmap_font.load_font("/GothamBlack-54.bdf")  # Replace with the path to your font file

# Create a Group for the text
text_group = displayio.Group()

# Create a text label
text_area = adafruit_display_text.label.Label(font, color=0xFFFFFF)
text_area.anchor_point = (0.5, 0.5)  # Center the text
text_area.anchored_position = (display.width // 2, display.height // 2)  # Position the text in the center
text_group.append(text_area)

# Set up GPIO button
button = digitalio.DigitalInOut(BUTTON_PIN)
button.switch_to_input(pull=digitalio.Pull.UP)

# Initialize I2C
i2c = board.I2C()
# Initialize the Seesaw (I2C rotary encoder)
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
encoder_button = DIO.DigitalIO(seesaw, 24)
# Variable to keep track of the number
number = load_number()
locked = False
last_button_state = button.value
last_encoder_button_state = encoder_button.value
last_position = encoder.position
last_displayed_number = 0

# Display the initial number
update_display()

while True:
    if not locked:
        # Read encoder position
        position = encoder.position
        if position != last_position:
            diff = last_position - position  # Reverse the direction
            number += diff
            number = max(0, number)  # Prevent negative numbers
            save_number(number)
            update_display()
            last_position = position
            print("Encoder position changed. Number:", number)

        # Read button state
        current_button_state = button.value
        if current_button_state != last_button_state:
            if not current_button_state:
                number += 1
                save_number(number)
                update_display()
                print("Button pressed. Number:", number)
            last_button_state = current_button_state
    else:
        time.sleep(0.5)  # Reduce polling frequency when locked
        position = encoder.position
        last_position = position

    # Check for rotary encoder button press
    current_encoder_button_state = encoder_button.value
    if current_encoder_button_state != last_encoder_button_state:
        if last_encoder_button_state:
            locked = not locked
            update_display()
            print("Encoder button pressed. Locked:", locked)
        last_encoder_button_state = current_encoder_button_state

    # Check if rotary encoder is held for 2 seconds to reset counter
    if not encoder_button.value:  # Button is pressed
        if not locked:
            press_time = time.monotonic()
            while not encoder_button.value:
                if time.monotonic() - press_time > 2:
                    number = 0
                    save_number(number)
                    locked = False
                    update_display()
                    print("Encoder button held for 2 seconds. Counter reset.")
                    break
        time.sleep(0.1)  # Debounce delay
