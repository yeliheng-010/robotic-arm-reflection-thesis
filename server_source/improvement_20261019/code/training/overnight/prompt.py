from training.qlora.data import SYSTEM as BASE_SYSTEM

FORMAT = 'text-reflection-v2'
SYSTEM = BASE_SYSTEM + (
    ' Parameter meanings: replan asks for a new action plan; reground re-localizes the objects. '
    'lift_height is vertical lift before horizontal transport; larger time_scale is slower. '
    'grasp_offset and place_offset are added to the perceived world grasp/release positions, '
    'in world XYZ metres. Evidence definitions: grasp_residual_xy = commanded grasp XY minus '
    'object XY; placement_residual_xy = final object XY minus container centre XY. '
    'Respect vector axis order and sign. Reason quantitatively from the supplied measurements '
    'and current offsets. Changes are absolute values, not increments.'
)
