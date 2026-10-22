/**
 * Every backend endpoint the frontend calls, in one place. Components and hooks import from here
 * rather than calling apiClient directly. Standard CRUD resources come from createResource();
 * one-off endpoints are plain functions that resolve to the response body (res.data).
 * Paths are relative to the /api/v1 base url (see api/client.js) and match backend/v1/app/routers.
 */
import apiClient from '../api/client.js';
import { createResource } from './resourceService.js';

// facility hierarchy (facility > building > floor > seat), see backend/v1/app/routers/facilities.py
export const facilitiesService = createResource('/facilities');
// a whole facility with generated floors/seats in one go, or more buildings for an existing one
export const setupFacility = (data) => apiClient.post('/facilities/setup', data).then((res) => res.data);
// counts of what deleting a facility/building/floor/seat would remove, path e.g. '/buildings'
export const fetchDeleteImpact = (path, id) => apiClient.get(`${path}/${id}/delete-impact`).then((res) => res.data);
export const addBuildingsBulk = (facilityId, data) => apiClient.post(`/facilities/${facilityId}/buildings/bulk`, data).then((res) => res.data);
export const buildingsService = createResource('/buildings');
export const floorsService = createResource('/floors');
export const seatsService = createResource('/seats');
// list filters (status, priority, facility_id, ...) go in the params, see routers/incidents.py
export const incidentsService = createResource('/incidents');
// engineer profiles (specialty, availability, capacity), each linked to a user with the Engineer role
export const engineersService = createResource('/engineers');

// user accounts, admin only on the backend
export const usersService = createResource('/users');

// public: a new user sets their password for the account an admin created for their email
export const registerAccount = (data) => apiClient.post('/auth/register', data).then((res) => res.data);

// notes are nested under their incident. the backend hides internal notes from employees
export const incidentNotesService = (incidentId) => createResource(`/incidents/${incidentId}/notes`);

// status change trail for one incident, oldest first
export const fetchIncidentHistory = (incidentId) => apiClient.get(`/incidents/${incidentId}/history`).then((res) => res.data);

// one page of the "Needs attention" list. params: {kind, facility_id, building_id, limit, offset}
export const fetchAttention = (params) => apiClient.get('/analytics/attention', {params}).then((res) => res.data);

// everything the dashboard shows, scoped to the logged in user. params: {start, end, facility_id, building_id, tz}
// (facility_id is a list and only applies to admins). called by hooks/useDashboard.js
export const fetchDashboard = (params) => apiClient.get('/analytics/dashboard', {params}).then((res) => res.data);
