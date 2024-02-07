```
 _   _               _       ____  ____    ___   _   _ 
| | | |  __ _   ___ | | __  / ___||  _ \  / _ \ | \ | |
| |_| | / _` | / __|| |/ / | |  _ | |_) || | | ||  \| |
|  _  || (_| || (__ |   <  | |_| ||  __/ | |_| || |\  |
|_| |_| \__,_| \___||_|\_\  \____||_|     \___/ |_| \_|
```

# ZTE-F061v6 firmware mod kit

> [!NOTE] 
> This mod kit is for change software version and hardware version of ZTE-F061v6

> [!IMPORTANT]  
> This script is currently working only for ZTE F601v6 shipped with TIM (V6.0.10N40) or OpenFiber (V6.0.10P6N7) firmware
> All other versions were not tested, USE IT AT YOUR OWN RISK!

> [!NOTE] 
> Before proceed make sure to have a GOOD BACKUP of all your ONT partitions.

> [!CAUTION] 
> Please refer to Hack-GPON Wiki for how-to: https://hack-gpon.org/ont-zte-f601/


## Prerequisites

- Linux
- python 3.3+

## Usage

Place in the same folder of `ZTE_Firmware_Mod.py` `kernel0` or `kernel1` mtd dump: see https://hack-gpon.org/ont-zte-f601/
```
python ZTE_Firmware_Mod.py <mtd dump> <software version> fw_mod.bin
```

> [!TIP] 
> For help, run the script with the following parameters: `-h`. 

> [!TIP] 
> For change hardware version edit this line: https://github.com/hack-gpon/ZTE-F601v6-mod-kit/blob/main/ZTE_Firmware_Mod.py#L79
> beware that if you want to exchange the hardware version in the future, you must have the original `kernel10` or `kernel11`!
