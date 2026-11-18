# Morning assistant (Raspberry Pi 5)

Talks you through your morning and reminds you what to take when you leave.

| When | It says |
|---|---|
| You get up (3 motion events within a minute, between 05:30 and 10:00) | "Good morning! Turn on the coffee machine, then go take a shower." |
| You come back after 4+ minutes with no motion | "Welcome back. Make your coffee and iron your shirt." |
| The front door opens | "Before you go: don't forget your keys, car key, phone and laptop. And check the iron is off." |
| You have left and a tagged item is still in the house | "You left without your keys." (also sent to your phone if `notify.url` is set) |

All wording, times and thresholds are in `config.toml`.

## Parts

- Raspberry Pi 5 with Raspberry Pi OS (Bookworm)
- A speaker (USB or Bluetooth; the Pi 5 has no headphone jack)
- PIR motion sensor (HC-SR501 or similar) in the bedroom: VCC to 5V, GND to GND, OUT to GPIO17
- Magnetic reed switch on the front door: one wire to GPIO27, the other to GND
- Optional: Bluetooth tags on your keys and laptop bag, for the "you left without it" check
- Optional: a smart plug with a local HTTP API (Shelly, Tasmota) to switch the coffee machine on

If the door is too far from the Pi for a wire, any device that can call
`http://<pi>:8765/event/door_opened` works instead (set `http.host = "0.0.0.0"`).

## Install

```bash
sudo apt install -y python3-gpiozero espeak-ng
sudo apt install -y python3-bleak        # only for Bluetooth tags
cp config.example.toml config.toml       # then edit
python3 -m morning_assistant --config config.toml
```

Try it without any sensors:

```bash
curl localhost:8765/event/motion         # three times = wake up
curl localhost:8765/event/door_opened
curl localhost:8765/state
```

Start on boot:

```bash
mkdir -p ~/.config/systemd/user
cp morning-assistant.service ~/.config/systemd/user/   # edit WorkingDirectory if needed
systemctl --user enable --now morning-assistant
sudo loginctl enable-linger $USER
```

## Tests

```bash
python3 -m unittest discover -s tests
```

## Limits

- The Pi reminds you about the coffee and the shirt; it does not make or iron them.
  A smart plug can power the coffee machine if it starts brewing when power returns.
  Do not put the iron on a remote-controlled plug.
- One motion sensor cannot tell people apart. It assumes you live alone or it is in your room.
- Without tags, the leaving reminder lists every item every time. It cannot see what is in your pocket.
