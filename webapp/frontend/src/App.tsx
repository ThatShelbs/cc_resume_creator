import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AppShell } from "./components/layout/AppShell";
import { TooltipProvider } from "./components/ui/overlays";
import { Skeleton } from "./components/ui/primitives";
import { JobCenter } from "./features/jobs/JobCenter";
import { ProjectsPage } from "./features/projects/ProjectsPage";
import { useTheme } from "./lib/theme";

// The workspace pulls in the PDF viewer (pdf.js), so it loads on demand.
const WorkspacePage = lazy(() => import("./features/workspace/WorkspacePage"));
const NewProjectPage = lazy(() => import("./features/projects/NewProjectPage"));
const ProfilePage = lazy(() => import("./features/profile/ProfilePage"));
const ResumePage = lazy(() => import("./features/resume/ResumePage"));
const EvidencePage = lazy(() => import("./features/evidence/EvidencePage"));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage"));
const OnboardingPage = lazy(() => import("./features/onboarding/OnboardingPage"));
const NotFoundPage = lazy(() => import("./features/NotFoundPage"));

function PageFallback() {
  return (
    <div className="mx-auto grid max-w-6xl gap-4 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

export function App() {
  const { resolved } = useTheme();
  return (
    <TooltipProvider delayDuration={300}>
      <JobCenter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/welcome" element={<OnboardingPage />} />
            <Route element={<AppShell />}>
              <Route index element={<ProjectsPage />} />
              <Route path="projects/new" element={<NewProjectPage />} />
              <Route path="projects/:id" element={<WorkspacePage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="resume" element={<ResumePage />} />
              <Route path="evidence" element={<EvidencePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </Suspense>
      </JobCenter>
      <Toaster theme={resolved} position="bottom-right" richColors closeButton toastOptions={{ className: "font-sans" }} />
    </TooltipProvider>
  );
}
