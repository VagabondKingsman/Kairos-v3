import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { Home } from "@/pages/Home";
import { Agent } from "@/pages/Agent";
import { Dashboard } from "@/pages/Dashboard";
import { BacktestDetail } from "@/pages/BacktestDetail";
import { RunDetail } from "@/pages/RunDetail";
import { Compare } from "@/pages/Compare";
import { Strategies } from "@/pages/Strategies";
import { Execution } from "@/pages/Execution";
import { MLCenter } from "@/pages/MLCenter";
import { Settings } from "@/pages/Settings";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/agent", element: <Agent /> },
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/backtest/:runId", element: <BacktestDetail /> },
      { path: "/runs/:runId", element: <RunDetail /> },
      { path: "/compare", element: <Compare /> },
      { path: "/strategies", element: <Strategies /> },
      { path: "/execution", element: <Execution /> },
      { path: "/ml", element: <MLCenter /> },
      { path: "/settings", element: <Settings /> },
    ],
  },
]);
