/**
 * Per-ticket edit rules. Mirrors ALLOWED_TRANSITIONS / EDITABLE_FIELDS in backend/v1/app/routers/incidents.py.
 *
 * Unlike permissions.js (what a role can do anywhere), these depend on how the user relates to one
 * ticket: an engineer can only update status on tickets assigned to them, a reporter can only
 * close/reopen once it's resolved, etc. The backend enforces the same rules, this just keeps
 * the form from offering changes that would be rejected.
 *
 * Used by pages/IncidentsPage.jsx for each form field's editableBy rule and the status dropdown.
 * If you change a rule here, change it in the backend too (and vice versa).
 */
import { ROLES } from './permissions.js';

// which statuses each status can move to (before any per-actor limits below).
// Resolved -> Open / In Progress is a reopen
export const ALLOWED_TRANSITIONS = {
    'Open': ['In Progress', 'Blocked', 'Resolved', 'Closed'],
    'In Progress': ['Open', 'Blocked', 'Resolved'],
    'Blocked': ['In Progress', 'Resolved'],
    'Resolved': ['Open', 'In Progress', 'Closed'],
    'Closed': ['Open'],
};

// how a user relates to one ticket. mirrors Actor in backend/v1/app/routers/incidents.py
export const ACTORS = {ADMIN: 'admin', ASSIGNEE: 'assignee', REPORTER: 'reporter'};

// fields each actor may change (admins may change every field). mirrors EDITABLE_FIELDS in the backend
const REPORTER_FIELDS = new Set([
    'title', 'description', 'category', 'priority', 'is_escalated', 'escalation_reason',
    'status', 'building_id', 'floor_id', 'seat_id',
]);
const ASSIGNEE_FIELDS = new Set(['status', 'blocked_reason']);

/**
 * Works out how a user relates to a ticket, checked in priority order: admin, then the assigned
 * engineer, then the reporter. An engineer who isn't the assignee is treated as a reporter if they
 * raised the ticket.
 * @param incident the incident row (needs assignee_id, reporter_id)
 * @param user the decoded token from useAuth(): {uid, role, ...}
 * @returns one of ACTORS, or null if they can't edit the ticket at all
 */
export function incidentActor(incident, user) {
    if (!incident || !user) return null;
    if (user.role === ROLES.FACILITY_ADMIN) return ACTORS.ADMIN;
    if (user.role === ROLES.ENGINEER && incident.assignee_id === user.uid) return ACTORS.ASSIGNEE;
    if (incident.reporter_id === user.uid) return ACTORS.REPORTER;
    return null;
}

/**
 * Whether the user may change one field of an existing ticket.
 * @param incident the saved incident row (rules use its saved status, not the form's current value)
 * @param user the decoded token from useAuth()
 * @param {string} fieldName an IncidentUpdate field, e.g. 'status' or 'blocked_reason'
 * @returns {boolean}
 */
export function canEditIncidentField(incident, user, fieldName) {
    const actor = incidentActor(incident, user);
    if (actor === ACTORS.ADMIN) return true;
    if (actor === ACTORS.REPORTER) {
        // reporters can't touch a closed ticket, an admin has to reopen it
        if (incident.status === 'Closed' || !REPORTER_FIELDS.has(fieldName)) return false;
        // their only status change is closing or reopening a resolved ticket
        return fieldName !== 'status' || incident.status === 'Resolved';
    }
    if (actor === ACTORS.ASSIGNEE) return ASSIGNEE_FIELDS.has(fieldName);
    return false;
}

/**
 * Statuses offered in the form: the current one plus every move this user may make from it.
 * Reporters may only close or reopen a resolved ticket; assignees may never close a ticket or
 * move it out of Closed (only admins and reporters close tickets). Same checks as the
 * status workflow in backend/v1/app/routers/incidents.py.
 * @returns {string[]} [] if the incident has no status yet (e.g. the create form)
 */
export function statusChoices(incident, user) {
    const current = incident?.status;
    if (!current) return [];
    const actor = incidentActor(incident, user);
    let next = ALLOWED_TRANSITIONS[current] ?? [];
    if (actor === ACTORS.REPORTER) {
        next = current === 'Resolved' ? ['Open', 'Closed'] : [];
    } else if (actor === ACTORS.ASSIGNEE) {
        next = current === 'Closed' ? [] : next.filter((status) => status !== 'Closed');
    } else if (actor !== ACTORS.ADMIN) {
        next = [];
    }
    return [current, ...next];
}
