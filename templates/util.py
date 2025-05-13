def return_thickness(filename):
    if filename in ["all-floor-plans-1.dxf", "bangalow-new-plan-1.dxf", "bungalow-new-plan-2.dxf"]:
        return 15
    elif filename in ["apartment-design.dxf", "complex-architecture.dxf", "cricket-ground.dxf", "podium-architecture.dxf", "sport-complex-1.dxf"]:
        return 0.1
    else:
        return -1
