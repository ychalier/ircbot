# IRC Bot

## Getting Started

### Prerequisites

You'll need Python 3. You may want to use a virtual environment. Needed modules
are `irc` and `blinker`. You can install them with:

```bash
pip install -r requirements.txt
```

### Installing

Simply **clone** the repository and create a **configuration file** in JSON format,
with the following format:

```json
{
    "host": "irc.example.com",
    "port": 6667,
    "password": "VeryBadPassword",
    "nickname": "pybot",
    "realname": "PyBot",
    "channels": [
        "#testbot"
    ]
}
```

If the configuration file you created is named `config.json` and is located
within the cloned folder, you do not need to specify its path to the script.
Otherwise, you can pass the path as an argument with the `-c` option.
For instance:

```bash
python ircbot.py -c ~/.ircbot.json
```

## Available Commands

Name | Description
---- | -----------
!guess | Play a "more-or-less" game
!hello | Prints a welcoming message
!info  | Prints bot information
