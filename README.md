BUFR Tools
==========

A suite of utilities and scripts to forge a BUFR file, or decode one.


Installation
------------

It is advisable to use conda for development and usage of this project, although it's not strictly
necessary. This README assumes the use of conda, however.


To install the environment:

```
conda env create -f environment.yml
```


Usage
=====

Encoding Wildlife Computers netCDF Profiles
-------------------------------------------

The `wildlife_computers` module provides a command-line interface for encoding a Wildlife Computers'
netCDF profile dataset as a BUFR message.

Usage:
```
python bufrtools/encoding/wildlife_computers.py -o <output bufr file> <netCDF path>
```

The following table contains the expanded sequence of descriptors for temperature salinity profiles
and trajectories originating from marine animal tags.

+--------+--------+---------------------------------------------------------------------------------+----------------------------------------------------+
| parent | fxy    | text                                                                            | Subtitle                                           |
+--------+--------+---------------------------------------------------------------------------------+----------------------------------------------------+
| 315013 | 315013 | (Met-ocean observations from marine animal tags) (Sequence)                     |                                                    |
| 315013 | 301150 | WIGOS identifier (Sequence)                                                     |                                                    |
| 301150 | 001125 | WIGOS identifier series (Numeric)                                               |                                                    |
| 301150 | 001126 | WIGOS issuer of identifier (Numeric)                                            |                                                    |
| 301150 | 001127 | WIGOS issue number (Numeric)                                                    |                                                    |
| 301150 | 001128 | WIGOS local identifier (character) (CCITT IA5)                                  |                                                    |
| 315013 | 001087 | WMO marine observing platform extended identifier (Numeric)                     | WMO number where assigned                          |
| 315013 | 208032 | Change width of CCITT IA5 field (Operator)                                      | change width to 32 characters                      |
| 315013 | 001019 | Long station or site name (CCITT IA5)                                           | Platform ID, e.g. ct145-933-BAT2-19 (max 32-chars) |
| 315013 | 208000 | Change width of CCITT IA5 field (Operator)                                      | Cancel change width                                |
| 315013 | 003001 | Surface Station Type (Code table)                                               | 11 (Marine Animal)                                 |
| 315013 | 022067 | Instrument type for water temperature/salinity profile measurement (Code table) | Set to 995 (attached to marine animal)             |
| 315013 | 001051 | Platform Transmitter ID number (CCITT IA5)                                      | e.g. Argos PTT                                     |
| 315013 | 002148 | Data collection and/or location system (Code table)                             |                                                    |
| 315013 | 112000 | Delayed replication of 12 descriptors (Replication)                             |                                                    |
| 315013 | 031001 | Delayed descriptor replication factor (Numeric)                                 |                                                    |
| 315013 | 008021 | Time significance (Code table)                                                  | set to 26, time of last known position             |
| 315013 | 301011 | (Year, month, day) (Sequence)                                                   |                                                    |
| 301011 | 004001 | Year (a)                                                                        |                                                    |
| 301011 | 004002 | Month (mon)                                                                     |                                                    |
| 301011 | 004003 | Day (d)                                                                         |                                                    |
| 315013 | 301012 | (Hour, minute) (Sequence)                                                       |                                                    |
| 301012 | 004004 | Hour (h)                                                                        |                                                    |
| 301012 | 004005 | Minute (min)                                                                    |                                                    |
| 315013 | 301021 | (Latitude / longitude (high accurracy)) (Sequence)                              |                                                    |
| 301021 | 005001 | Latitude (high accuracy) (deg)                                                  |                                                    |
| 301021 | 006001 | Longitude (high accuracy) (deg)                                                 |                                                    |
| 315013 | 001012 | Direction of motion of moving observing platform (degree true)                  |                                                    |
| 315013 | 001014 | Platform drift speed (high precision) (m/s)                                     |                                                    |
| 315013 | 033022 | Quality of buoy satellite transmission (Code table)                             |                                                    |
| 315013 | 033023 | Quality of buoy location (Code table)                                           |                                                    |
| 315013 | 033027 | Location quality class (range of radius of 66% confidence) (Code table)         |                                                    |
| 315013 | 007063 | Depth below sea/water surface (m)                                               |                                                    |
| 315013 | 022045 | Sea / Water Temperature (K)                                                     |                                                    |
| 315013 | 008021 | Time significance (Code table)                                                  | Set to missing / cancel                            |
| 315013 | 107000 | Delayed replication of 7 descriptors (Replication)                              |                                                    |
| 315013 | 031001 | Delayed descriptor replication factor (Numeric)                                 |                                                    |
| 315013 | 301011 | (Year, month, day) (Sequence)                                                   |                                                    |
| 301011 | 004001 | Year (a)                                                                        |                                                    |
| 301011 | 004002 | Month (mon)                                                                     |                                                    |
| 301011 | 004003 | Day (d)                                                                         |                                                    |
| 315013 | 301012 | (Hour, minute) (Sequence)                                                       |                                                    |
| 301012 | 004004 | Hour (h)                                                                        |                                                    |
| 301012 | 004005 | Minute (min)                                                                    |                                                    |
| 315013 | 301021 | (Latitude / longitude (high accurracy)) (Sequence)                              |                                                    |
| 301021 | 005001 | Latitude (high accuracy) (deg)                                                  |                                                    |
| 301021 | 006001 | Longitude (high accuracy) (deg)                                                 |                                                    |
| 315013 | 001079 | Unique identifier for the profile (CCITT IA5)                                   | Profile ID                                         |
| 315013 | 001023 | Observation sequence number (Numeric)                                           | Upcast number                                      |
| 315013 | 022056 | Direction of profile (Code table)                                               | Set to 0 (ascending / upwards)                     |
| 315013 | 306035 | Temperature and salinity profile (Sequence)                                     |                                                    |
| 306035 | 112000 | Delayed replication of 12 descriptors (Replication)                             |                                                    |
| 306035 | 031002 | Extended delayed descriptor replication factor (Numeric)                        |                                                    |
| 306035 | 007062 | Depth below sea/water surface (m)                                               | In metres                                          |
| 306035 | 008080 | Qualifier for GTSPP quality flag (Code table)                                   | = 13 Depth at a level                              |
| 306035 | 033050 | Global GTSPP quality flag (Code table)                                          |                                                    |
| 306035 | 007065 | Water pressure (Pa)                                                             |                                                    |
| 306035 | 008080 | Qualifier for GTSPP quality flag (Code table)                                   | = 10 Pressure at a level                           |
| 306035 | 033050 | Global GTSPP quality flag (Code table)                                          |                                                    |
| 306035 | 022043 | Sea/water temperature (K)                                                       |                                                    |
| 306035 | 008080 | Qualifier for GTSPP quality flag (Code table)                                   | = 11 Temperature at a level                        |
| 306035 | 033050 | Global GTSPP quality flag (Code table)                                          |                                                    |
| 306035 | 022064 | Salinity (0/00)                                                                 | = 12 Salinity at a level                           |
| 306035 | 008080 | Qualifier for GTSPP quality flag (Code table)                                   |                                                    |
| 306035 | 033050 | Global GTSPP quality flag (Code table)                                          |                                                    |
+--------+--------+---------------------------------------------------------------------------------+----------------------------------------------------+
