import { useCallback, useEffect, useState } from 'react';
import { fetchDashboard } from '../services/index.js';
import { getErrorMessage } from './useResource.js';
import { formatShortDate } from '../utils/format.js';

const DAY_MS = 86_400_000;
const PRESET_DAYS = {'7d': 7, '30d': 30, '90d': 90};
// trend buckets follow the viewer's days, not the server's
const TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

// range: {preset: '7d' | '30d' | '90d' | 'all'} or {preset: 'custom', from: 'YYYY-MM-DD', to: 'YYYY-MM-DD'}
export const DEFAULT_RANGE = {preset: '30d'};

function rangeToParams(range) {
    if (range.preset === 'all') {
        return {};
    }
    if (range.preset === 'custom') {
        // whole local days: from 00:00 on the first day up to 00:00 after the last one
        const start = new Date(`${range.from}T00:00`);
        const end = new Date(`${range.to}T00:00`);
        end.setDate(end.getDate() + 1);
        return {start: start.toISOString(), end: end.toISOString()};
    }
    return {start: new Date(Date.now() - PRESET_DAYS[range.preset] * DAY_MS).toISOString()};
}

// "last 30 days", "all time", "Oct 1 – Oct 21"
export function describeRange(range) {
    if (range.preset === 'all') {
        return 'all time';
    }
    if (range.preset === 'custom') {
        return `${formatShortDate(`${range.from}T00:00`)} – ${formatShortDate(`${range.to}T00:00`)}`;
    }
    return `last ${PRESET_DAYS[range.preset]} days`;
}

// "previous 30 days" etc. -- what the trend arrows compare against (all time has nothing to compare to)
export function describePreviousRange(range) {
    if (range.preset === 'all') {
        return null;
    }
    return range.preset === 'custom' ? 'the period before' : `previous ${PRESET_DAYS[range.preset]} days`;
}

// loads GET /analytics/dashboard for the range/facilities/building, keeping the last result on screen while reloading.
// enabled=false holds the request (e.g. until we know an admin's home facility)
export function useDashboard({range, facilityIds = [], buildingId = null, enabled = true}) {
    const [refreshCount, setRefreshCount] = useState(0);
    const requestKey = JSON.stringify({range, facilityIds, buildingId, refreshCount});
    const [result, setResult] = useState({key: null, data: null, error: null, loadedAt: null});

    useEffect(() => {
        if (!enabled) {
            return;
        }
        const request = JSON.parse(requestKey);
        let cancelled = false;
        fetchDashboard({
            ...rangeToParams(request.range),
            facility_id: request.facilityIds,
            building_id: request.buildingId ?? undefined,
            tz: TIME_ZONE,
        })
            .then((data) => !cancelled && setResult({key: requestKey, data, error: null, loadedAt: new Date()}))
            .catch((err) => !cancelled && setResult((prev) => ({...prev, key: requestKey, error: getErrorMessage(err)})));
        return () => {
            cancelled = true;
        };
    }, [enabled, requestKey]);

    const refresh = useCallback(() => setRefreshCount((count) => count + 1), []);

    return {
        data: result.data,
        error: result.error,
        loading: result.key !== requestKey,
        loadedAt: result.loadedAt,
        refresh,
    };
}
