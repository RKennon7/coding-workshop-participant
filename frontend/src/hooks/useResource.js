import { useCallback, useEffect, useMemo, useState } from 'react';

// pull a readable message out of an axios error (FastAPI puts it in response.data.detail)
export function getErrorMessage(error) {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string') {
        return detail;
    }
    if (Array.isArray(detail)) {
        // pydantic validation errors
        return detail.map((d) => d.msg).join(', ');
    }
    return error?.message || 'Something went wrong';
}

// loads a resource's rows and wraps its create/update/remove calls so the list
// reloads after every change. service comes from services/index.js
export function useResource(service, {enabled = true} = {}) {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(enabled);
    const [error, setError] = useState(null);

    const reload = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            setRows(await service.list());
        } catch (err) {
            setError(getErrorMessage(err));
        } finally {
            setLoading(false);
        }
    }, [service]);

    // initial load (and again if the service changes). state is only set once the request settles,
    // never synchronously inside the effect, and responses that arrive after the component moved on
    // (unmounted, or switched to another service) are ignored
    useEffect(() => {
        if (!enabled) {
            return;
        }
        let cancelled = false;
        service.list()
            .then((data) => {
                if (!cancelled) {
                    setRows(data);
                    setError(null);
                }
            })
            .catch((err) => !cancelled && setError(getErrorMessage(err)))
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [enabled, service]);

    const create = async (data) => {
        const created = await service.create(data);
        await reload();
        return created;
    };

    const update = async (id, data) => {
        const updated = await service.update(id, data);
        await reload();
        return updated;
    };

    const remove = async (id) => {
        await service.remove(id);
        await reload();
    };

    return {rows, loading, error, reload, create, update, remove};
}

// turns a resource's rows into select options: [{value, label, row}]
// row is kept so options can be filtered by other fields (e.g. floors by building)
export function useOptions(service, getLabel, {getValue = (row) => row.id, enabled = true} = {}) {
    const {rows} = useResource(service, {enabled});
    // getLabel/getValue are usually inline arrow functions, so only recompute when the rows change
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return useMemo(() => rows.map((row) => ({value: getValue(row), label: getLabel(row), row})), [rows]);
}

// {value: label} lookup for showing a name in a grid column instead of a foreign key id
export function toLabelMap(options) {
    return Object.fromEntries(options.map((option) => [option.value, option.label]));
}
