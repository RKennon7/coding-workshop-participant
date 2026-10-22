import apiClient from '../api/client.js';
import { createResource } from './resourceService.js';

export const facilitiesService = createResource('/facilities');
// a whole facility with generated floors/seats in one go, or more buildings for an existing one
export const setupFacility = (data) => apiClient.post('/facilities/setup', data).then((res) => res.data);
// counts of what deleting a facility/building/floor/seat would remove, path e.g. '/buildings'
export const fetchDeleteImpact = (path, id) => apiClient.get(`${path}/${id}/delete-impact`).then((res) => res.data);
export const addBuildingsBulk = (facilityId, data) => apiClient.post(`/facilities/${facilityId}/buildings/bulk`, data).then((res) => res.data);
export const buildingsService = createResource('/buildings');
export const floorsService = createResource('/floors');
export const seatsService = createResource('/seats');
export const incidentsService = createResource('/incidents');
export const engineersService = createResource('/engineers');

export const usersService = createResource('/users');

// public: a new user sets their password for the account an admin created for their email
export const registerAccount = (data) => apiClient.post('/auth/register', data).then((res) => res.data);

// notes are nested under their incident
export const incidentNotesService = (incidentId) => createResource(`/incidents/${incidentId}/notes`);

// status change trail for one incident, oldest first
export const fetchIncidentHistory = (incidentId) => apiClient.get(`/incidents/${incidentId}/history`).then((res) => res.data);

// everything the dashboard shows, scoped to the logged in user. params: {start, end, building_id, tz}
export const fetchDashboard = (params) => apiClient.get('/analytics/dashboard', {params}).then((res) => res.data);
