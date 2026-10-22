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
// params are sent as query params on list() (e.g. filters), and the list reloads when they change
export function useResource(service, {enabled = true, params} = {}) {
    // params are usually built inline, so compare them by value instead of by reference
    const paramsKey = JSON.stringify(params ?? {});
    // rows/error from the last finished request, tagged with the params they were loaded for
    const [result, setResult] = useState({key: null, rows: [], error: null});
    const [reloading, setReloading] = useState(false);

    const reload = useCallback(async () => {
        setReloading(true);
        try {
            const rows = await service.list(JSON.parse(paramsKey));
            setResult({key: paramsKey, rows, error: null});
        } catch (err) {
            setResult((prev) => ({...prev, error: getErrorMessage(err)}));
        } finally {
            setReloading(false);
        }
    }, [service, paramsKey]);

    // initial load (and again if the service or params change). state is only set once the request settles,
    // never synchronously inside the effect, and responses that arrive after the component moved on
    // (unmounted, or switched to other params) are ignored
    useEffect(() => {
        if (!enabled) {
            return;
        }
        let cancelled = false;
        service.list(JSON.parse(paramsKey))
            .then((rows) => !cancelled && setResult({key: paramsKey, rows, error: null}))
            .catch((err) => !cancelled && setResult((prev) => ({key: paramsKey, rows: prev.rows, error: getErrorMessage(err)})));
        return () => {
            cancelled = true;
        };
    }, [enabled, service, paramsKey]);

    // loading until the current params' request has finished (stale rows stay visible meanwhile)
    const loading = enabled && (result.key !== paramsKey || reloading);

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

    return {rows: result.rows, loading, error: result.error, reload, create, update, remove};
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
