# api.py

from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request

from tune_management.profiles import ProfileManager, UnknownProfile
from tune_management.tune_manager import ApprovalRefused, TuneManager, TuneNotApproved, TuneNotFound
from tune_management.tune_switcher import SOURCES, TuneSwitcher

api = Blueprint('tune_api', __name__, url_prefix='/api/cars/<int:car_id>')

def _switcher(car_id):
    # Apps can set SWITCHER_FACTORY to supply a backend / engine rpm source per car.
    factory = current_app.config.get('SWITCHER_FACTORY', TuneSwitcher)
    return factory(car_id)

def _error(status, reason):
    return jsonify(ok=False, reason=reason), status

@api.get('/tunes')
def list_tunes(car_id):
    return jsonify([{'id': t['id'], 'name': t['name'], 'created_at': t['created_at'], 'origin': t['origin'],
                     'approved': t['approved_at'] is not None, 'approved_by': t['approved_by'],
                     'approved_at': t['approved_at']}
                    for t in TuneManager(car_id).list_tunes()])

@api.post('/tunes/<int:tune_id>/approve')
def approve_tune(car_id, tune_id):
    body = request.get_json(silent=True) or {}
    try:
        tune = TuneManager(car_id).approve_tune(tune_id, body.get('approved_by'), body.get('source'), body.get('note'))
    except TuneNotFound as e:
        return _error(404, str(e))
    except ApprovalRefused as e:
        return _error(403, str(e))
    return jsonify(ok=True, tune={k: tune[k] for k in ('id', 'name', 'origin', 'approved', 'approved_by', 'approved_at')})

@api.get('/profiles')
def list_profiles(car_id):
    return jsonify(ProfileManager(car_id).list_profiles())

@api.put('/profiles/<name>')
def assign_profile(car_id, name):
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get('tune_id'), int):
        return _error(400, "Body must be JSON with an integer tune_id")
    profiles = ProfileManager(car_id)
    try:
        profiles.assign(name, body['tune_id'])
        return jsonify(ok=True, profile=profiles.get(name))
    except (UnknownProfile, TuneNotFound) as e:
        return _error(404, str(e))
    except TuneNotApproved as e:
        return _error(409, str(e))

@api.get('/active')
def active(car_id):
    return jsonify(_switcher(car_id).active())

@api.post('/switch')
def switch(car_id):
    body = request.get_json(silent=True) or {}
    source, profile, tune_id = body.get('source'), body.get('profile'), body.get('tune_id')
    if source not in SOURCES:
        return _error(400, f"source must be one of {', '.join(SOURCES)}")
    if (profile is None) == (tune_id is None):
        return _error(400, "Pass exactly one of profile or tune_id")
    return _switch_response(_switcher(car_id).switch(source, profile=profile, tune_id=tune_id))

@api.post('/revert')
def revert(car_id):
    source = (request.get_json(silent=True) or {}).get('source')
    if source not in SOURCES:
        return _error(400, f"source must be one of {', '.join(SOURCES)}")
    return _switch_response(_switcher(car_id).revert_to_stock(source))

def _switch_response(result):
    status = {None: 200, 'not_found': 404}.get(result.error, 409)
    return jsonify(asdict(result)), status

@api.get('/history')
def history(car_id):
    return jsonify(_switcher(car_id).history(limit=request.args.get('limit', 50, type=int)))
