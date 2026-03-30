import fs from 'fs';
import path from 'path';
const PROJECT_ROOT = path.resolve(process.cwd(), '../../');
const STATE_FILE = path.join(PROJECT_ROOT, '.forgewright', 'pipeline-state.json');
export const PIPELINE_PHASES = [
    "Phase 0: Project Initiation & Mode Selection",
    "Phase 1: Research & Discovery (PM/BA/Architect)",
    "Phase 2: Execution (BE/FE/Engine Engineers)",
    "Phase 3: QA & Hardening",
    "Phase 4: Release & Deployment"
];
const DEFAULT_STATE = {
    currentPhase: 0,
    currentMode: null,
    history: [],
    status: 'IDLE'
};
function ensureDirSync(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}
export function getState() {
    if (!fs.existsSync(STATE_FILE)) {
        saveState(DEFAULT_STATE);
        return DEFAULT_STATE;
    }
    try {
        const raw = fs.readFileSync(STATE_FILE, 'utf-8');
        return JSON.parse(raw);
    }
    catch (e) {
        console.error("Failed to read state, returning default", e);
        return DEFAULT_STATE;
    }
}
export function saveState(state) {
    ensureDirSync(path.dirname(STATE_FILE));
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
}
export function startPipeline(mode) {
    const state = getState();
    state.currentPhase = 1;
    state.currentMode = mode;
    state.status = 'IN_PROGRESS';
    state.history.push(`Started pipeline in mode: ${mode}`);
    saveState(state);
    return `Successfully started pipeline in ${mode} mode. You are now at Phase 1: Research & Discovery. Follow the primary Orchestrator rules.`;
}
export function advancePhase() {
    const state = getState();
    if (state.status === 'WAITING_FOR_GATE') {
        return `Error: You cannot advance the phase yet. The current phase is frozen pending human-in-the-loop (HITL) gate approval.`;
    }
    if (state.currentPhase >= PIPELINE_PHASES.length - 1) {
        state.status = 'COMPLETED';
        state.history.push(`Pipeline completed.`);
        saveState(state);
        return `Success: Pipeline is now Fully Completed.`;
    }
    state.currentPhase += 1;
    const phaseName = PIPELINE_PHASES[state.currentPhase];
    state.history.push(`Advanced to ${phaseName}`);
    saveState(state);
    return `Successfully advanced to ${phaseName}. Check the Forgewright instructions for roles required in this phase.`;
}
export function requestGateApproval(message) {
    const state = getState();
    state.status = 'WAITING_FOR_GATE';
    state.history.push(`Requested Gate Approval: ${message}`);
    saveState(state);
    return `System is now locked. Ask the user for explicit approval to pass the gate: "${message}".`;
}
export function approveGate() {
    const state = getState();
    if (state.status !== 'WAITING_FOR_GATE') {
        return 'Error: System is not waiting for any gate approval.';
    }
    state.status = 'IN_PROGRESS';
    state.history.push('Gate approved by user.');
    saveState(state);
    return 'Gate successfully approved. Proceed to next step or advance phase.';
}
