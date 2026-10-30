import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  state,
  snapshot,
  createRideRequest,
  driverRespond,
  listShareCandidates,
  proposeShare,
  decideShare,
  resetDemoState
} from "./state.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());

// Always start clean: no pre-made requests, all drivers idle.
resetDemoState();

app.get("/api/graph", (req, res) => {
  res.json(state.graph);
});

app.get("/api/state", (req, res) => {
  res.json(snapshot());
});

app.post("/api/request", (req, res) => {
  const { userName, fromCityId, toCityId, wantsSharing, numPersons } = req.body ?? {};
  if (!userName || !fromCityId || !toCityId) {
    res.status(400).json({ ok: false, error: "userName, fromCityId, toCityId are required." });
    return;
  }
  const result = createRideRequest({ userName, fromCityId, toCityId, wantsSharing, numPersons });
  res.status(result.ok ? 200 : 400).json(result);
});

app.post("/api/driver/respond", (req, res) => {
  const { driverId, requestId, accept } = req.body ?? {};
  if (!driverId || !requestId || typeof accept !== "boolean") {
    res.status(400).json({ ok: false, error: "driverId, requestId, accept(boolean) are required." });
    return;
  }
  const result = driverRespond({ driverId, requestId, accept });
  res.status(result.ok ? 200 : 400).json(result);
});

app.get("/api/share/candidates", (req, res) => {
  const requestId = req.query.requestId;
  if (!requestId) {
    res.status(400).json({ ok: false, error: "requestId is required." });
    return;
  }
  const result = listShareCandidates(String(requestId));
  res.status(result.ok ? 200 : 400).json(result);
});

app.post("/api/share/propose", (req, res) => {
  const { requestId, rideId, pickupCityId, dropCityId } = req.body ?? {};
  if (!requestId || !rideId || !pickupCityId || !dropCityId) {
    res.status(400).json({ ok: false, error: "requestId, rideId, pickupCityId, dropCityId are required." });
    return;
  }
  const result = proposeShare({ requestId, rideId, pickupCityId, dropCityId });
  res.status(result.ok ? 200 : 400).json(result);
});

app.post("/api/share/decide", (req, res) => {
  const { rideId, proposalId, accept } = req.body ?? {};
  if (!rideId || !proposalId || typeof accept !== "boolean") {
    res.status(400).json({ ok: false, error: "rideId, proposalId, accept(boolean) are required." });
    return;
  }
  const result = decideShare({ rideId, proposalId, accept });
  res.status(result.ok ? 200 : 400).json(result);
});

app.post("/api/reset", (req, res) => {
  res.json({ ok: true, state: resetDemoState() });
});

// Static client
const clientDir = path.join(__dirname, "..", "client");
app.use("/", express.static(clientDir));

const port = process.env.PORT ? Number(process.env.PORT) : 5174;
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`Web UI running at http://localhost:${port}`);
});

