import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";
import { I18nProvider } from "@/lib/i18n";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { router } from "./router";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <ErrorBoundary>
        <RouterProvider router={router} />
      </ErrorBoundary>
      <Toaster
        position="bottom-right"
        richColors
        closeButton
        duration={3500}
        theme="dark"
      />
    </I18nProvider>
  </StrictMode>
);
