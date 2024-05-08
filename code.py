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
import alarm
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


def save_state():
    if locked:
        print("Locking in Memory")
        microcontroller.nvm[1] = 1
    else:
        print("Unlocking in Memory")
        microcontroller.nvm[1] = 0


def load_state():
    return bool(microcontroller.nvm[1])


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


# Configuration for CS pin (for the OLED display):
CS_PIN = board.D7
# Configuring button and encoder
BUTTON_PIN = board.D3
ENCODER_BUTTON_PIN = 24  # Pin number for the button on the rotary encoder

time.sleep(1.5)
print("Booting...")
# Initialize I2C
i2c = board.I2C()
# Initialize the Seesaw (I2C rotary encoder)
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
encoder_button = DIO.DigitalIO(seesaw, 24)
locked = load_state()
print("IS DEVICE LOCKED:" + str(locked))
if (not locked):
    # Variable to keep track of the number
    number = load_number()
    # Set up GPIO button
    button = digitalio.DigitalInOut(BUTTON_PIN)
    button.switch_to_input(pull=digitalio.Pull.UP)
    last_button_state = button.value
    # SPI and display initialization
    displayio.release_displays()
    spi = board.SPI()
    framebuffer = sharpdisplay.SharpMemoryFramebuffer(spi, CS_PIN, 160, 68)
    display = framebufferio.FramebufferDisplay(framebuffer)

    # Load the font
    # Replace with the path to your font file
    font = bitmap_font.load_font("/GothamBlack-54.bdf")

    # Create a Group for the text
    text_group = displayio.Group()

    # Create a text label
    text_area = adafruit_display_text.label.Label(font, color=0xFFFFFF)
    text_area.anchor_point = (0.5, 0.5)  # Center the text
    # Position the text in the center
    text_area.anchored_position = (display.width // 2, display.height // 2)
    text_group.append(text_area)
    # Display the initial number
    update_display()

last_encoder_button_state = encoder_button.value
last_position = encoder.position
last_displayed_number = 0


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
            press_time = time.monotonic()
            while not button.value:
                if time.monotonic() - press_time > 3:
                    number = 0
                    save_number(number)
                    locked = False
                    update_display()
                    print("Button held for 3 seconds. Counter reset.")
                    time.sleep(2)
                    break
                time.sleep(0.1)  # Debounce delay
    else:
        if not encoder_button.value:
            locked = False
            save_state()
            print("Unlocked")
            # Variable to keep track of the number
            number = load_number()
            # Set up GPIO button
            button = digitalio.DigitalInOut(BUTTON_PIN)
            button.switch_to_input(pull=digitalio.Pull.UP)
            last_button_state = button.value
            # SPI and display initialization
            displayio.release_displays()
            spi = board.SPI()
            framebuffer = sharpdisplay.SharpMemoryFramebuffer(
                spi, CS_PIN, 160, 68)
            display = framebufferio.FramebufferDisplay(framebuffer)

            # Load the font
            # Replace with the path to your font file
            font = bitmap_font.load_font("/GothamBlack-54.bdf")

            # Create a Group for the text
            text_group = displayio.Group()

            # Create a text label
            text_area = adafruit_display_text.label.Label(font, color=0xFFFFFF)
            text_area.anchor_point = (0.5, 0.5)  # Center the text
            # Position the text in the center
            text_area.anchored_position = (
                display.width // 2, display.height // 2)
            text_group.append(text_area)
            # Display the initial number
            update_display()
        else:
            sleep_time = 6
            time_alarm = alarm.time.TimeAlarm(
                monotonic_time=time.monotonic() + sleep_time)
            alarm.exit_and_deep_sleep_until_alarms(time_alarm)

    # Check for rotary encoder button press
    current_encoder_button_state = encoder_button.value
    if current_encoder_button_state != last_encoder_button_state:
        if last_encoder_button_state:
            locked = not locked
            update_display()
            print("Encoder button pressed. Locked:", locked)
            if (locked):
                displayio.release_displays()
                spi.deinit()
                encoder = None
                seesaw = None
                i2c.deinit()
            save_state()
            time.sleep(1)
        last_encoder_button_state = current_encoder_button_state
