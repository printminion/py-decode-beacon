# estimote.py
# estimote nearable advertisement data decoder
# Copyright (c) 2017 Misha M.-Kupriyanov (@printminion)
# MIT Licensed
#

import struct
from collections import namedtuple
import uuid

class estimote:
    @staticmethod
    def decode(ad_struct):
        """Ad structure decoder for Estimote nearable
        Returns a dictionary with the following fields if the ad structure is a
        valid mfg spec iBeacon structure:
          adstruct_bytes: <int> Number of bytes this ad structure consumed
          type: <string> 'estimote nearable' for Estimote nearable
          uuid: <string> UUID
          major: <int> iBeacon Major
          minor: <int> iBeacon Minor
          rssi_ref: <int> Reference signal @ 1m in dBm
        If this isn't a valid iBeacon structure, it returns a dict with these
        fields:
          adstruct_bytes: <int> Number of bytes this ad structure consumed
          type: None for unknown
        """
        # Get the length of the ad structure (including the length byte)
        adstruct_bytes = ord(ad_struct[0]) + 1
        # Create the return object
        ret = {'adstruct_bytes': adstruct_bytes, 'type': None}
        # Is the length correct and is our data long enough?
        if adstruct_bytes == 0x03 and adstruct_bytes <= len(ad_struct):
            # Decode the ad structure assuming iBeacon format
            iBeaconData = namedtuple('iBeaconData',
                                     'adstruct_bytes '  # B
                                     + 'adstruct_type '  # B
                                     + 'mfg_id_low '  # B
                                       'mfg_id_high '  # B
                                       'ibeacon_id '  # B
                                       'ibeacon_data_len '  # B
                                     # data
                                       'manufacturer_id '  # BB 1-2
                                       'nearable_protocol_version '  # B 3-3
                                     + 'uuid '  # 4s - 3-11
                                       'major '  # H 7-9
                                       'minor '  # H 9-11
                                       'hardwareVersion '  # 11 
                                       'firmware_version '  # 12
                                       'temperature '  # 13
                                       'battery '  # 14
                                       'moving_indicator_and_battery_level '  # 15
                                       'acceleration_x '  # 16 i
                                       'acceleration_y '  # 17 i
                                       'acceleration_z '  # 18 i
                                     # 'current_motion_state_duration ' #19 i
                                     # 'previous_motion_state_duration ' #20 i
                                     # 'rssi_ref' #2 I
                                     )
            # https://docs.python.org/2/library/struct.html#format-characters
            # bd = iBeaconData._make(struct.unpack('>BBBBBB2s1s4sHHbb', ad_struct[3:22]))
            bd = iBeaconData._make(struct.unpack('>BBBBBB2s1s4sHHbbbbbbbb', ad_struct[3:28]))
            # bd = iBeaconData._make(struct.unpack('>BBBBBB2s1s4sHHbbHbbbbbb', ad_struct[3:30]))

            # print bd
            # ad_struct[0] === 0x5d & & ad_struct[1] == = 0x01 & & // company id
            # ad_struct[2] === 0x01) { // nearable version

            # Check whether all iBeacon specific values are correct
            if bd.adstruct_bytes == 0x03 and \
                            bd.adstruct_type == 0x03 and \
                            bd.mfg_id_low == 0x0F and \
                            bd.mfg_id_high == 0x18 and \
                            bd.ibeacon_id == 0x17 and \
                            bd.ibeacon_data_len == 0xff:
                # This is a valid iBeacon ad structure
                # Fill in the return structure with the data we extracted
                ret['type'] = 'estimote nearable'
                ret['uuid'] = str(uuid.UUID("d0d3fa86-ca76-45ec-9bd9-6af4" + bd.uuid.encode('hex')))
                ret['major'] = bd.major
                ret['minor'] = bd.minor
                # ret['rssi_ref'] = bd.rssi_ref

                ret['manufacturer_id'] = bd.manufacturer_id.encode('hex')  # String
                # ret['nearable_protocol_version'] = bd.nearable_protocol_version.encode('hex')  # String
                # ret['identifier'] = None  # String
                ret['hardwareVersion'] = estimote.parse_hardware_version(bd.hardwareVersion)  # String
                ret['firmwareVersion'] = estimote.parse_firmware_version(bd.firmware_version)
                ret['bootloaderVersion'] = estimote.parse_bootloader_version(bd.firmware_version)  # String
                # ret['firmwareState'] = None  # FirmwareState
                ret['temperature'] = estimote.parse_temperature(bd.temperature)  # double
                # ret['rssi'] = None  # int
                ret['isMoving'] = (bd.moving_indicator_and_battery_level & 0x40) != 0  # boolean

                ret['xAcceleration'] = estimote.parse_acceleration(bd.acceleration_x)  # double
                ret['yAcceleration'] = estimote.parse_acceleration(bd.acceleration_y)  # double
                ret['zAcceleration'] = estimote.parse_acceleration(bd.acceleration_z)  # double

                ret['orientation'] = estimote.calculate_orientation(ret['isMoving'], ret['xAcceleration'],
                                                                    ret['yAcceleration'],
                                                                    ret['zAcceleration'])  # Orientation
                # ret['currentMotionStateDuration'] = None  # long
                # ret['lastMotionStateDuration'] = None  # long
                ret['batteryLevel'] = estimote.parse_battery_level(bd.battery,
                                                                   bd.moving_indicator_and_battery_level)  # BatteryLevel

                # ret['power'] = None  # BroadcastingPower
                # ret['region'] = None  # Region
                # ret['nearableType'] = None  # NearableType
                # ret['color'] = None  # Color
        # Return the object
        return ret

    @staticmethod
    def parse_region(data):
        pass

    @staticmethod
    def parse_firmware_state(data):
        pass

    @staticmethod
    def parse_hardware_version(data):

        if data == 1:
            return "D3.2"

        if data == 2:
            return "D3.3"

        if data == 3:
            return "D3.4"

        if data == 4:  # 0x4
            return "SB0"

        return "unknown"

    @staticmethod
    def parse_firmware_version(data):
        """

        :rtype: string
        :param byte data: 
        :return: 
        """

        if data == -127:
            return 'SA1.0.0'

        if data == -126:
            return 'SA1.0.1'

        return 'unknown'

    @staticmethod
    def parse_bootloader_version(data):

        if data == 0x1:
            return 'SB1.0.0'

        return 'unknown'

    @staticmethod
    def parse_temperature(bytes):

        # temperatureRaw = (((bytes[12] & 255) << 8) + (bytes[11] & 255) & 4095) << 4
        #
        # realTemperature = 0
        #
        # if ((temperatureRaw & '') == 0):
        #     realTemperature = (double)(temperatureRaw & '\uffff') / 256.0D
        #     return Math.ceil(realTemperature * 1000.0D) / 1000.0D
        # else:
        #     realTemperature = (double)((temperatureRaw & 32767) - '') / 256.0D
        #     return Math.floor(realTemperature * 1000.0D) / 1000.0D

        rawTemperature = (bytes & 0x0fff) << 4

        if rawTemperature & 0x8000:
            return ((rawTemperature & 0x7fff) - 32768.0) / 256.0
        else:
            return rawTemperature / 256.0

    @staticmethod
    def parse_battery_level(battery_data, moving_indicator_and_battery_level):

        battery_voltage = 0

        # if (moving_indicator_and_battery_level.readUInt8(15) & 0x80) == 0:
        if (moving_indicator_and_battery_level & 0x80) == 0:
            # rawBatteryLevel = (moving_indicator_and_battery_level.readUInt8(15) << 8) + ((battery_data.readUInt8(14) >> 4) & 0x3ff)
            rawBatteryLevel = (moving_indicator_and_battery_level << 8) + ((battery_data >> 4) & 0x3ff)

            battery_voltage = 3.6 * rawBatteryLevel / 1023.0

        if battery_voltage >= 2.95:
            return 'high'
        elif battery_voltage < 2.95 and battery_voltage >= 2.7:
            return 'medium'
        elif battery_voltage > 0.0:
            return 'low'
        else:
            return 'unknown'

    @staticmethod
    def parse_acceleration(data):

        # manufacturerData.readInt8(16) * 15.625

        return data * 15.62

    @staticmethod
    def calculate_orientation(is_moving, acceleration_x, acceleration_y, acceleration_z):

        if is_moving:
            return 'UNKNOWN'

        if acceleration_z > 800.0:
            return 'HORIZONTAL_UPSIDE_DOWN'

        if acceleration_z < -800.0:
            return 'HORIZONTAL'

        if acceleration_x > 700.0:
            return 'LEFT_SIDE'

        if acceleration_x < -700.0:
            return 'RIGHT_SIDE'

        if acceleration_y > 800.0:
            return 'VERTICAL'

        if acceleration_y < -800.0:
            return 'VERTICAL_UPSIDE_DOWN'

