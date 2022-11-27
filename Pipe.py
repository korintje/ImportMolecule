pipeRadius = 0.1
    
sel = ui.selectEntity('Select a path to create a pipe', 'Edges,SketchCurves')
selObj = sel.entity

comp = design.rootComponent

# create path
feats = comp.features
chainedOption = adsk.fusion.ChainedCurveOptions.connectedChainedCurves
if adsk.fusion.BRepEdge.cast(selObj):
    chainedOption = adsk.fusion.ChainedCurveOptions.tangentChainedCurves
path = adsk.fusion.Path.create(selObj, chainedOption)
path = feats.createPath(selObj)

# create profile
planes = comp.constructionPlanes
planeInput = planes.createInput()
planeInput.setByDistanceOnPath(selObj, adsk.core.ValueInput.createByReal(0))
plane = planes.add(planeInput)

sketches = comp.sketches
sketch = sketches.add(plane)

center = plane.geometry.origin
center = sketch.modelToSketchSpace(center)
sketch.sketchCurves.sketchCircles.addByCenterRadius(center, pipeRadius)
profile = sketch.profiles[0]

# create sweep
sweepFeats = feats.sweepFeatures
sweepInput = sweepFeats.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
sweepFeat = sweepFeats.add(sweepInput)