def decide(manifest, collection_decision):
    if manifest and manifest['gate']['quantitative_ready']:
        return 'stage_preparation'
    if collection_decision and not collection_decision['advance']:
        return 'development_required'
    return 'collecting'
