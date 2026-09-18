import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Dashboard from "./pages/Dashboard";
import EvidenceExplorer from "./pages/EvidenceExplorer";
import Profile from "./pages/Profile";
import ReasoningGraph from "./pages/ReasoningGraph";
import Scientist from "./pages/Scientist";
import "leaflet/dist/leaflet.css";

export default function App() {
  return (
    <div className="flex min-h-screen">
      <NavBar />
      <main className="flex-1 bg-paper overflow-y-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scientist" element={<Scientist />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/evidence" element={<EvidenceExplorer />} />
          <Route path="/reasoning" element={<ReasoningGraph />} />
        </Routes>
      </main>
    </div>
  );
}
