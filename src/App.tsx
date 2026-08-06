import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Signals from "@/pages/Signals";
import Calculator from "@/pages/Calculator";
import RiskManager from "@/pages/RiskManager";
import Journal from "@/pages/Journal";
import SettingsPage from "@/pages/SettingsPage";
import Setup from "@/pages/Setup";
import Backtest from "@/pages/Backtest";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/calculator" element={<Calculator />} />
            <Route path="/risk" element={<RiskManager />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/backtest" element={<Backtest />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
