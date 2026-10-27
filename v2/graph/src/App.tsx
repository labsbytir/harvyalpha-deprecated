import { useCallback, useEffect, useState } from "react";
import {
  AnalyticsDashboard,
  CubeProvider,
  type DashboardConfig,
} from "drizzle-cube/client";
import "drizzle-cube/client/styles.css";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  ApiError,
  deleteDashboard,
  listDashboards,
  saveDashboard,
} from "./api";
import { MONO } from "./theme";

const INITIAL_CUBE_CONFIG: DashboardConfig = {
  portlets: [
    {
      id: "portlet-observations-by-source",
      title: "Observations by Source Platform",
      query: JSON.stringify({
        measures: ["Observations.count"],
        dimensions: ["Observations.source"],
      }),
      chartType: "bar",
      w: 6,
      h: 4,
      x: 0,
      y: 0,
    },
    {
      id: "portlet-observations-timeseries",
      title: "Daily Observation Activity",
      query: JSON.stringify({
        measures: ["Observations.count"],
        timeDimensions: [{ dimension: "Observations.observedAt", granularity: "day" }],
      }),
      chartType: "line",
      w: 6,
      h: 4,
      x: 6,
      y: 0,
    },
    {
      id: "portlet-observations-count",
      title: "Total Ingested Events",
      query: JSON.stringify({
        measures: ["Observations.count"],
      }),
      chartType: "kpiNumber",
      w: 4,
      h: 3,
      x: 0,
      y: 4,
    },
    {
      id: "portlet-objects-type",
      title: "Entities by Type",
      query: JSON.stringify({
        measures: ["Objects.count"],
        dimensions: ["Objects.typeId"],
      }),
      chartType: "pie",
      w: 4,
      h: 3,
      x: 4,
      y: 4,
    },
    {
      id: "portlet-links-type",
      title: "Graph Relationships",
      query: JSON.stringify({
        measures: ["Links.count"],
        dimensions: ["Links.linkType"],
      }),
      chartType: "table",
      w: 4,
      h: 3,
      x: 8,
      y: 4,
    },
  ],
  layoutMode: "grid",
  grid: {
    cols: 12,
    rowHeight: 80,
    minW: 2,
    minH: 2,
  },
};

export default function App() {
  const [cubeConfig, setCubeConfig] = useState<DashboardConfig>(INITIAL_CUBE_CONFIG);
  const [title, setTitle] = useState("Operational Overview");
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [saved, setSaved] = useState<{ id: string; title: string; layout?: any }[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [authRequired, setAuthRequired] = useState(false);

  const refreshSaved = useCallback(async () => {
    try {
      const res = await listDashboards();
      setSaved(
        (res.dashboards || []).map((d) => ({
          id: d.id,
          title: d.title,
          layout: typeof d.layout_json === "string" ? JSON.parse(d.layout_json) : d.layout_json,
        }))
      );
      setAuthRequired(false);
    } catch (e) {
      if (e instanceof ApiError && e.authRequired) setAuthRequired(true);
    }
  }, []);

  useEffect(() => {
    void refreshSaved();
  }, [refreshSaved]);

  const handleSave = async () => {
    try {
      const savedRec = await saveDashboard(
        title.trim() || "Untitled Dashboard",
        cubeConfig,
        cubeConfig.portlets || [],
        currentId || undefined
      );
      setCurrentId(savedRec.id);
      setNotice(`Saved dashboard: ${title}`);
      await refreshSaved();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Save failed.");
    }
  };

  const handleLoad = (id: string) => {
    const item = saved.find((s) => s.id === id);
    if (!item) return;
    setCurrentId(item.id);
    setTitle(item.title);
    if (item.layout?.portlets) {
      setCubeConfig(item.layout as DashboardConfig);
      setNotice(`Loaded ${item.title}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDashboard(id);
      if (currentId === id) {
        setCurrentId(null);
        setCubeConfig(INITIAL_CUBE_CONFIG);
      }
      setNotice("Dashboard deleted.");
      await refreshSaved();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  const handleReset = () => {
    setCurrentId(null);
    setTitle("Operational Overview");
    setCubeConfig(INITIAL_CUBE_CONFIG);
    setNotice("Reset to default configuration.");
  };

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {/* MUI Header Shell */}
      <Card variant="outlined" sx={{ bgcolor: "#121214", borderColor: "#27272a" }}>
        <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", sm: "center" }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <TextField
                size="small"
                variant="outlined"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                sx={{
                  width: { xs: "100%", sm: 260 },
                  "& input": { fontFamily: MONO, fontSize: "0.9rem", fontWeight: 600, color: "#f4f4f5" },
                }}
              />
              <Chip
                label="DRIZZLE-CUBE"
                size="small"
                sx={{
                  bgcolor: "#18181b",
                  color: "#a1a1aa",
                  border: "1px solid #27272a",
                  fontFamily: MONO,
                  fontSize: "0.7rem",
                  fontWeight: 600,
                }}
              />
            </Stack>

            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              {saved.length > 0 && (
                <Select
                  size="small"
                  displayEmpty
                  value={currentId || ""}
                  onChange={(e) => handleLoad(e.target.value)}
                  sx={{
                    minWidth: 160,
                    bgcolor: "#18181b",
                    fontFamily: MONO,
                    fontSize: "0.8rem",
                    "& .MuiSelect-select": { py: 0.8 },
                  }}
                >
                  <MenuItem value="" disabled sx={{ fontFamily: MONO, fontSize: "0.8rem" }}>
                    <em>Load saved...</em>
                  </MenuItem>
                  {saved.map((s) => (
                    <MenuItem key={s.id} value={s.id} sx={{ fontFamily: MONO, fontSize: "0.8rem" }}>
                      {s.title}
                    </MenuItem>
                  ))}
                </Select>
              )}

              <Button
                variant="contained"
                size="small"
                onClick={handleSave}
                sx={{
                  bgcolor: "#f4f4f5",
                  color: "#09090b",
                  fontWeight: 600,
                  fontFamily: MONO,
                  "&:hover": { bgcolor: "#e4e4e7" },
                }}
              >
                Save
              </Button>

              {currentId && (
                <Button
                  variant="outlined"
                  size="small"
                  color="error"
                  onClick={() => handleDelete(currentId)}
                  sx={{ fontFamily: MONO }}
                >
                  Delete
                </Button>
              )}

              <Button
                variant="outlined"
                size="small"
                onClick={handleReset}
                sx={{ color: "#a1a1aa", borderColor: "#27272a", fontFamily: MONO, "&:hover": { borderColor: "#3f3f46" } }}
              >
                Reset
              </Button>
            </Stack>
          </Stack>

          {notice && (
            <Alert
              severity="info"
              onClose={() => setNotice(null)}
              sx={{ mt: 1.5, bgcolor: "#18181b", border: "1px solid #27272a", color: "#f4f4f5", fontFamily: MONO, fontSize: "0.8rem" }}
            >
              {notice}
            </Alert>
          )}

          {authRequired && (
            <Alert
              severity="warning"
              sx={{ mt: 1.5, bgcolor: "#1e1b12", border: "1px solid #78350f", color: "#fde68a", fontFamily: MONO, fontSize: "0.8rem" }}
            >
              Sign in to save or persist customized analytics dashboards.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Drizzle Cube Body with MUI Theme CSS Variable Bridge */}
      <Box
        sx={{
          "--dc-surface": "#121214",
          "--dc-surface-secondary": "#18181b",
          "--dc-surface-tertiary": "#27272a",
          "--dc-surface-hover": "#27272a",
          "--dc-text": "#f4f4f5",
          "--dc-text-secondary": "#a1a1aa",
          "--dc-text-muted": "#71717a",
          "--dc-border": "#27272a",
          "--dc-border-secondary": "#3f3f46",
          "--dc-card-bg": "#121214",
          "--dc-card-bg-hover": "#18181b",
          "--dc-card-border": "#27272a",
          "--dc-primary": "#f4f4f5",
          "--dc-primary-hover": "#e4e4e7",
          "--dc-primary-content": "#09090b",
          "--dc-radius-sm": "4px",
          "--dc-radius-md": "6px",
          "--dc-radius-lg": "8px",
          bgcolor: "#09090b",
          borderRadius: 2,
          minHeight: 600,
          "& .dc-dashboard-section": {
            bgcolor: "#121214 !important",
            borderColor: "#27272a !important",
          },
          "& .react-grid-item": {
            bgcolor: "#121214",
            borderRadius: "6px",
            border: "1px solid #27272a",
          },
        }}
      >
        <CubeProvider apiOptions={{ apiUrl: "/api/v2/cube" }}>
          <AnalyticsDashboard
            config={cubeConfig}
            editable={true}
            onConfigChange={(newCfg) => setCubeConfig(newCfg)}
          />
        </CubeProvider>
      </Box>
    </Box>
  );
}
