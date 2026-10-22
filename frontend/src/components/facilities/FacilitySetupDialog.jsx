import { useState } from 'react';
import {
    Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, IconButton, MenuItem,
    Radio, RadioGroup, Stack, Step, StepLabel, Stepper, TextField, Tooltip, Typography, useMediaQuery,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined';
import { addBuildingsBulk, setupFacility } from '../../services/index.js';
import { getErrorMessage } from '../../hooks/useResource.js';

const STEPS = ['Facility', 'Buildings', 'Review'];
// mirrors the limits in backend/v1/app/schemas/facility.py
const MAX_FLOORS = 100;
const MAX_SEATS_PER_FLOOR = 200;
const MAX_SEATS_TOTAL = 5000;

// "North Tower" -> "NT", "Annex" -> "AN": the prefix generated seat codes start with
function suggestCode(name) {
    const words = name.trim().split(/\s+/).filter(Boolean).map((w) => w.replace(/[^A-Za-z0-9]/g, '')).filter(Boolean);
    if (words.length === 0) return '';
    const code = words.length === 1 ? words[0].slice(0, 2) : words.map((w) => w[0]).join('');
    return code.slice(0, 4).toUpperCase();
}

let nextKey = 1;
const newBuilding = () => ({key: nextKey++, name: '', code: '', codeEdited: false, floors: 1, seats: 10});

const seatCode = (code, floor, seat) => `${code}-${floor}-${String(seat).padStart(2, '0')}`;

// per-row problems, keyed by field, plus a message for the whole plan
function validate(buildings) {
    const errors = {};
    const count = (values) => values.reduce((acc, v) => ({...acc, [v]: (acc[v] ?? 0) + 1}), {});
    const names = count(buildings.map((b) => b.name.trim().toLowerCase()).filter(Boolean));
    const codes = count(buildings.map((b) => b.code).filter(Boolean));
    for (const b of buildings) {
        const e = {};
        if (!b.name.trim()) e.name = 'Required';
        else if (names[b.name.trim().toLowerCase()] > 1) e.name = 'Used twice';
        if (!/^[A-Z0-9]{1,10}$/.test(b.code)) e.code = 'Letters/digits';
        else if (codes[b.code] > 1) e.code = 'Used twice';
        if (!(b.floors >= 1 && b.floors <= MAX_FLOORS)) e.floors = `1–${MAX_FLOORS}`;
        if (!(b.seats >= 0 && b.seats <= MAX_SEATS_PER_FLOOR)) e.seats = `0–${MAX_SEATS_PER_FLOOR}`;
        if (Object.keys(e).length) errors[b.key] = e;
    }
    const totalSeats = buildings.reduce((sum, b) => sum + (b.floors || 0) * (b.seats || 0), 0);
    const planError = buildings.length === 0 ? 'Add at least one building'
        : totalSeats > MAX_SEATS_TOTAL ? `That's ${totalSeats} seats, at most ${MAX_SEATS_TOTAL} can be created at once` : null;
    return {errors, planError, totalSeats, valid: !planError && Object.keys(errors).length === 0};
}

function BuildingRow({building, errors = {}, onChange, onRemove, canRemove}) {
    const numberProps = (max) => ({htmlInput: {min: 0, max, inputMode: 'numeric'}});
    return (
        <Box sx={{display: 'grid', gridTemplateColumns: {xs: '1fr 1fr', sm: 'minmax(0, 2.2fr) 90px 90px 110px 40px'}, gap: 1.5, alignItems: 'start'}}>
            <TextField
                label="Building name"
                value={building.name}
                // the code follows the name until the admin types their own
                onChange={(e) => onChange({name: e.target.value, ...(!building.codeEdited && {code: suggestCode(e.target.value)})})}
                error={Boolean(errors.name)}
                helperText={errors.name}
                sx={{gridColumn: {xs: '1 / -1', sm: 'auto'}}}
                autoFocus={!building.name}
            />
            <TextField
                label="Code"
                value={building.code}
                onChange={(e) => onChange({code: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10), codeEdited: true})}
                error={Boolean(errors.code)}
                helperText={errors.code}
            />
            <TextField
                label="Floors"
                type="number"
                value={building.floors}
                onChange={(e) => onChange({floors: e.target.value === '' ? '' : Number(e.target.value)})}
                error={Boolean(errors.floors)}
                helperText={errors.floors}
                slotProps={numberProps(MAX_FLOORS)}
            />
            <TextField
                label="Seats / floor"
                type="number"
                value={building.seats}
                onChange={(e) => onChange({seats: e.target.value === '' ? '' : Number(e.target.value)})}
                error={Boolean(errors.seats)}
                helperText={errors.seats}
                slotProps={numberProps(MAX_SEATS_PER_FLOOR)}
            />
            <Tooltip title="Remove building">
                <span>
                    <IconButton onClick={onRemove} disabled={!canRemove} aria-label="Remove building" sx={{mt: 0.25}}>
                        <DeleteOutlineIcon />
                    </IconButton>
                </span>
            </Tooltip>
        </Box>
    );
}

function ReviewRow({building}) {
    const seats = building.floors * building.seats;
    const floorRange = building.floors === 1 ? 'Floor 1' : `Floor 1–${building.floors}`;
    const seatRange = building.seats === 0 ? 'no seats'
        : `${seatCode(building.code, 1, 1)} … ${seatCode(building.code, building.floors, building.seats)}`;
    return (
        <Box sx={{py: 1, borderBottom: 1, borderColor: 'divider'}}>
            <Stack direction="row" spacing={1} sx={{alignItems: 'baseline', justifyContent: 'space-between'}}>
                <Typography variant="body2" sx={{fontWeight: 600}}>{building.name.trim()} <Typography component="span" variant="body2" color="text.secondary">({building.code})</Typography></Typography>
                <Typography variant="body2" sx={{fontWeight: 600, whiteSpace: 'nowrap'}}>{seats} seats</Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary">
                {building.floors} × {building.seats} seats · {floorRange} · {seatRange}
            </Typography>
        </Box>
    );
}

{/**
 * three-step wizard: facility (new, or an existing one to add buildings to) -> buildings with floor/seat counts
 * -> review the generated names, then one request creates everything (POST /facilities/setup or .../buildings/bulk)
 *  - facilityOptions: existing facilities [{value, label}] for "add to existing"
 *  - onCreated(result): {facility, buildings, floors, seats}
 */}
function FacilitySetupDialog({open, onClose, onCreated, facilityOptions}) {
    const fullScreen = useMediaQuery((theme) => theme.breakpoints.down('sm'));
    const [step, setStep] = useState(0);
    const [mode, setMode] = useState('new');
    const [facility, setFacility] = useState({name: '', address: ''});
    const [existingId, setExistingId] = useState('');
    const [buildings, setBuildings] = useState(() => [newBuilding()]);
    const [showErrors, setShowErrors] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const plan = validate(buildings);
    const facilityValid = mode === 'new' ? facility.name.trim() !== '' : existingId !== '';
    const facilityLabel = mode === 'new' ? facility.name.trim() : facilityOptions.find((o) => o.value === existingId)?.label;
    const totalFloors = buildings.reduce((sum, b) => sum + (b.floors || 0), 0);

    const updateBuilding = (key, changes) => setBuildings((prev) => prev.map((b) => (b.key === key ? {...b, ...changes} : b)));

    const next = () => {
        if ((step === 0 && !facilityValid) || (step === 1 && !plan.valid)) {
            setShowErrors(true);
            return;
        }
        setShowErrors(false);
        setStep(step + 1);
    };

    const create = async () => {
        setSaving(true);
        setError(null);
        const payload = {
            buildings: buildings.map((b) => ({name: b.name.trim(), code: b.code, floors: b.floors, seats_per_floor: b.seats})),
        };
        try {
            const result = mode === 'new'
                ? await setupFacility({...payload, name: facility.name.trim(), address: facility.address.trim() || null})
                : await addBuildingsBulk(existingId, payload);
            onCreated(result);
        } catch (err) {
            setError(getErrorMessage(err));
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onClose={saving ? undefined : onClose} fullScreen={fullScreen} maxWidth="md" fullWidth>
            <DialogTitle>Set up a facility</DialogTitle>
            <DialogContent dividers>
                <Stepper activeStep={step} alternativeLabel sx={{mb: 3}}>
                    {STEPS.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
                </Stepper>

                {step === 0 && (
                    <Stack spacing={2}>
                        <RadioGroup row value={mode} onChange={(e) => setMode(e.target.value)}>
                            <FormControlLabel value="new" control={<Radio />} label="New facility" />
                            <FormControlLabel value="existing" control={<Radio />} label="Add buildings to an existing facility" disabled={!facilityOptions.length} />
                        </RadioGroup>
                        {mode === 'new' ? (
                            <>
                                <TextField
                                    label="Facility name"
                                    placeholder="e.g. ACME West Campus"
                                    value={facility.name}
                                    onChange={(e) => setFacility({...facility, name: e.target.value})}
                                    error={showErrors && !facilityValid}
                                    helperText={showErrors && !facilityValid ? 'Required' : ' '}
                                    required
                                    autoFocus
                                />
                                <TextField label="Address" value={facility.address} onChange={(e) => setFacility({...facility, address: e.target.value})} />
                            </>
                        ) : (
                            <TextField
                                select
                                label="Facility"
                                value={existingId}
                                onChange={(e) => setExistingId(e.target.value)}
                                error={showErrors && !facilityValid}
                                helperText={showErrors && !facilityValid ? 'Pick a facility' : ' '}
                                required
                            >
                                {facilityOptions.map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
                            </TextField>
                        )}
                    </Stack>
                )}

                {step === 1 && (
                    <Stack spacing={2}>
                        <Typography variant="body2" color="text.secondary">
                            Floors are named <strong>Floor 1, Floor 2, …</strong> and seats <strong>CODE-floor-seat</strong>,
                            e.g. NT-3-02 is seat 2 on floor 3 of the building coded NT. Every floor gets the same number of seats.
                        </Typography>
                        {buildings.map((b) => (
                            <BuildingRow
                                key={b.key}
                                building={b}
                                errors={showErrors ? plan.errors[b.key] : undefined}
                                onChange={(changes) => updateBuilding(b.key, changes)}
                                onRemove={() => setBuildings((prev) => prev.filter((x) => x.key !== b.key))}
                                canRemove={buildings.length > 1}
                            />
                        ))}
                        <Stack direction="row" sx={{alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1}}>
                            <Button startIcon={<AddIcon />} onClick={() => setBuildings((prev) => [...prev, newBuilding()])}>Add building</Button>
                            <Typography variant="body2" color={plan.totalSeats > MAX_SEATS_TOTAL ? 'error' : 'text.secondary'}>
                                {buildings.length} building{buildings.length === 1 ? '' : 's'} · {totalFloors} floors · {plan.totalSeats} seats
                            </Typography>
                        </Stack>
                        {showErrors && plan.planError && <Alert severity="error">{plan.planError}</Alert>}
                    </Stack>
                )}

                {step === 2 && (
                    <Stack spacing={2}>
                        {error && <Alert severity="error">{error}</Alert>}
                        <Alert severity="info">
                            {mode === 'new' ? 'Creates' : 'Adds to'} <strong>{facilityLabel}</strong>: {buildings.length} building{buildings.length === 1 ? '' : 's'},{' '}
                            {totalFloors} floors and {plan.totalSeats} seats. You can rename or deactivate any of them afterwards.
                        </Alert>
                        <Box>{buildings.map((b) => <ReviewRow key={b.key} building={b} />)}</Box>
                    </Stack>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={saving}>Cancel</Button>
                <Box sx={{flex: 1}} />
                {step > 0 && <Button onClick={() => setStep(step - 1)} disabled={saving}>Back</Button>}
                {step < STEPS.length - 1
                    ? <Button variant="contained" onClick={next}>Next</Button>
                    : <Button variant="contained" onClick={create} disabled={saving}>{saving ? 'Creating…' : 'Create'}</Button>}
            </DialogActions>
        </Dialog>
    );
}

export default FacilitySetupDialog;
