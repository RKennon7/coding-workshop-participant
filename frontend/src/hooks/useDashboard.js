/**
 * Data loading for pages/DashboardPage.jsx: turns the toolbar's date range / facility / building
 * picks into a GET /analytics/dashboard call (backend/v1/app/routers/analytics.py), plus helpers
 * that describe the range in words for card captions.
 */
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

// range -> {start, end} query params as ISO timestamps. the backend treats start as inclusive and
// end as exclusive (defaulting to now), and omitting both means all time
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
    // presets are rolling windows ending now (computed when the request is sent, so refresh moves it forward)
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

/**
 * Loads GET /analytics/dashboard for the range/facilities/building, keeping the last result on screen while reloading.
 * enabled=false holds the request (e.g. until we know an admin's home facility).
 * The backend scopes the data to the caller's role (data.scope: 'all' | 'assigned' | 'reported');
 * facilityIds only has an effect for admins (empty = every facility).
 * @returns {{data, error, loading, loadedAt: Date | null, refresh: () => void}}
 *   loading is true until the current inputs' request settles; data is the last successful result
 */
export function useDashboard({range, facilityIds = [], buildingId = null, enabled = true}) {
    // bumping this changes requestKey, which re-runs the effect with otherwise identical inputs
    const [refreshCount, setRefreshCount] = useState(0);
    // inputs are objects/arrays often rebuilt each render, so compare them by value via one string key
    const requestKey = JSON.stringify({range, facilityIds, buildingId, refreshCount});
    // key = the requestKey this result belongs to (loading is derived from it below)
    const [result, setResult] = useState({key: null, data: null, error: null, loadedAt: null});

    useEffect(() => {
        if (!enabled) {
            return;
        }
        const request = JSON.parse(requestKey);
        // ignore a response that lands after the inputs changed again or the page unmounted
        let cancelled = false;
        fetchDashboard({
            ...rangeToParams(request.range),
            facility_id: request.facilityIds,
            building_id: request.buildingId ?? undefined,
            tz: TIME_ZONE,
        })
            .then((data) => !cancelled && setResult({key: requestKey, data, error: null, loadedAt: new Date()}))
            // on failure keep the previous data so the page can show it alongside the error
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
