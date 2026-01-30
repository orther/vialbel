# Print Settings

Bambu Studio profile for ASA filament on a Bambu Lab P1S.

## Layer and Structure

| Setting | Functional Parts | Non-Critical Parts |
|---------|------------------|--------------------|
| Layer height | 0.20mm | 0.28mm |
| Walls | 4 minimum | 4 minimum |
| Infill | 40% gyroid | 20% gyroid |

## Adhesion and Enclosure

- **Brim**: Enabled, 5mm width for warping prevention
- **Enclosure**: Required for ASA (P1S enclosure panels must be installed)

## Temperature

| Setting | Range | Recommended |
|---------|-------|-------------|
| Nozzle | 240-260C | 250C |
| Bed | 100-110C | 105C |

## Speed and Cooling

- **Print speed**: 60-80mm/s
- **First layer speed**: 20mm/s
- **Part cooling fan**: 30-50% after first layer

## ASA Shrinkage

ASA shrinks 0.4-0.7% during cooling. All part dimensions in this project account for this shrinkage. Do not apply additional scaling in the slicer.

## Print Orientation by Component

| Component | Orientation | Notes |
|-----------|-------------|-------|
| Peel plate | Flat side down | Peel edge faces up for smooth finish |
| Vial cradle | V-groove facing up | |
| Spool holder | Flange down | |
| Dancer arm | Flat on bed | |
| Guide bracket | L-shape vertical wall up | |
| Main frame | Flat base down | May need to split if exceeding 256mm build volume |
