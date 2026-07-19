# v13.19 Speed-Based Move Power

Electro Ball and Gyro Ball use only trusted final Speed, stage adjustment, and
side-specific Tailwind. Electro Ball brackets are <1x 40, <2x 60, <3x 80,
<4x 120, otherwise 150. Gyro Ball is `min(150, floor(25*opponent/self)+1)`.
Trick Room and ability/item/paralysis modifiers are excluded.
