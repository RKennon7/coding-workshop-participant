import { useState } from 'react';
import {
    Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControlLabel, MenuItem, Stack, TextField,
} from '@mui/material';
import { getErrorMessage } from '../../hooks/useResource.js';

{/**
 * add/edit form generated from a list of field definitions:
 *   {name, label, type: 'text'|'textarea'|'number'|'email'|'password'|'select'|'checkbox',
 *    options: [{value, label}] or (values, initialValues) => options, required (bool or (values) => bool),
 *    hideOnCreate, createOnly, hidden: (values) => bool, dependsOn: 'otherFieldName'}
 * isFieldEditable(field) decides which inputs are enabled, so the same form works for
 * full edits, partial edits (e.g. engineers changing status) and read-only viewing.
 * onSubmit receives the values of the editable fields only. children render under the fields.
 */}

function emptyValue(field) {
    if (field.defaultValue !== undefined) {
        return field.defaultValue;
    }
    return field.type === 'checkbox' ? false : '';
}

// form inputs use '' for empty, the api expects null (and numbers, not strings)
function toApiValue(field, value) {
    if (field.type === 'checkbox') {
        return Boolean(value);
    }
    if (value === '' || value === undefined) {
        return null;
    }
    return field.type === 'number' ? Number(value) : value;
}

export function isFieldVisible(field, mode, values) {
    if (mode === 'create' && field.hideOnCreate) return false;
    if (mode === 'edit' && field.createOnly) return false;
    return !field.hidden?.(values);
}

function EntityFormDialog({
    open,
    mode = 'create',
    title,
    fields,
    initialValues = {},
    isFieldEditable = () => true,
    onSubmit,
    onClose,
    children,
}) {
    const [values, setValues] = useState(() =>
        Object.fromEntries(fields.map((field) => [field.name, initialValues[field.name] ?? emptyValue(field)]))
    );
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const visibleFields = fields.filter((field) => isFieldVisible(field, mode, values));
    const editableFields = visibleFields.filter((field) => isFieldEditable(field));
    const readOnly = editableFields.length === 0;

    // changing a field clears any field that dependsOn it (e.g. new building -> clear floor)
    const setValue = (name, value) => setValues((prev) => {
        const next = {...prev, [name]: value};
        const clearDependents = (parentName) => fields
            .filter((field) => field.dependsOn === parentName)
            .forEach((field) => {
                next[field.name] = emptyValue(field);
                clearDependents(field.name);
            });
        clearDependents(name);
        return next;
    });

    const handleSubmit = async (event) => {
        event.preventDefault();
        setSaving(true);
        setError(null);
        try {
            const payload = Object.fromEntries(
                editableFields.map((field) => [field.name, toApiValue(field, values[field.name])])
            );
            await onSubmit(payload);
            onClose();
        } catch (err) {
            setError(getErrorMessage(err));
        } finally {
            setSaving(false);
        }
    };

    const renderField = (field) => {
        const disabled = saving || !isFieldEditable(field);
        const value = values[field.name];

        if (field.type === 'checkbox') {
            return (
                <FormControlLabel
                    key={field.name}
                    label={field.label}
                    disabled={disabled}
                    control={<Checkbox checked={Boolean(value)} onChange={(e) => setValue(field.name, e.target.checked)} />}
                />
            );
        }

        const options = typeof field.options === 'function' ? field.options(values, initialValues) : field.options;
        const required = typeof field.required === 'function' ? field.required(values) : field.required;
        return (
            <TextField
                key={field.name}
                label={field.label}
                name={field.name}
                type={['number', 'email', 'password'].includes(field.type) ? field.type : 'text'}
                value={value ?? ''}
                onChange={(e) => setValue(field.name, e.target.value)}
                required={required && !disabled}
                disabled={disabled}
                select={field.type === 'select'}
                multiline={field.type === 'textarea'}
                minRows={field.type === 'textarea' ? 3 : undefined}
                helperText={field.helperText}
                fullWidth
            >
                {field.type === 'select' && [
                    !required && <MenuItem key="__none" value=""><em>None</em></MenuItem>,
                    ...(options ?? []).map((option) => (
                        <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                    )),
                ]}
            </TextField>
        );
    };

    return (
        <Dialog
            open={open}
            onClose={saving ? undefined : onClose}
            maxWidth="sm"
            fullWidth
            slotProps={{paper: {component: 'form', onSubmit: handleSubmit}}}
        >
            <DialogTitle>{title}</DialogTitle>
            <DialogContent dividers>
                <Stack spacing={2}>
                    {error && <Alert severity="error">{error}</Alert>}
                    {visibleFields.map(renderField)}
                    {children}
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={saving}>{readOnly ? 'Close' : 'Cancel'}</Button>
                {!readOnly && (
                    <Button type="submit" variant="contained" disabled={saving}>
                        {mode === 'create' ? 'Create' : 'Save'}
                    </Button>
                )}
            </DialogActions>
        </Dialog>
    );
}

export default EntityFormDialog;
