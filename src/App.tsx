import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Activity, Tractor, Leaf, Box, Menu, Wallet } from 'lucide-react'
import { Toaster, toast } from 'sonner' // Added Sonner
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { SatelliteDialog } from '@/components/SatelliteDialog'
import { calculateOnionPrice, getSatelliteCoordinates, getSatelliteStatus } from '@/lib/simulator' // Imported logic

// Mock Hashes (Static for now, but could be dynamic too)
const initialHashes = Array.from({ length: 5 }, () =>
    "0x" + Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join("")
)

export default function App() {
    // State
    const [dieselTax, setDieselTax] = useState([30])
    const [exportBan, setExportBan] = useState(false)
    const [isConnected, setIsConnected] = useState(false)
    const [prices, setPrices] = useState<{ day: string; price: number }[]>([])
    const [isSyncing, setIsSyncing] = useState(false)
    const [history, setHistory] = useState<{ action: string, cost: string, time: string }[]>([
        { action: "Oracle Feed Sync", cost: "0.001", time: "Just now" }
    ])
    const [activeView, setActiveView] = useState<'dashboard' | 'live-feeds' | 'supply-chain'>('dashboard')

    // Satellite State
    const [coords, setCoords] = useState({ lat: "20.5937", lng: "78.9629" })
    const [satStatus, setSatStatus] = useState<"ACQUIRING" | "ANALYZING" | "TRANSMITTING">("ACQUIRING")

    // Effect: Recalculate Prices when Policy Changes
    useEffect(() => {
        // TODO: Replace this with a backend API call
        // Example: fetch(`/api/predict?tax=${dieselTax[0]}&ban=${exportBan}`)
        const newPrices = Array.from({ length: 30 }, (_, i) => ({
            day: `Day ${i + 1}`,
            price: calculateOnionPrice(dieselTax[0], i) + (exportBan ? -15 : 0) // Export ban crashes domestic price
        }))
        setPrices(newPrices)

        // Trigger Sync Pulse
        setIsSyncing(true)
        const timer = setTimeout(() => setIsSyncing(false), 1000)
        return () => clearTimeout(timer)
    }, [dieselTax, exportBan])

    // Helper: Add to Transaction History
    const addToHistory = (action: string, cost: string) => {
        const newLog = { action, cost, time: "Just now" }
        setHistory(prev => [newLog, ...prev])
    }

    // Effect: Satellite Animation Loop
    useEffect(() => {
        const interval = setInterval(() => {
            setCoords(getSatelliteCoordinates())
            setSatStatus(getSatelliteStatus())
        }, 3000) // Update every 3 seconds
        return () => clearInterval(interval)
    }, [])

    const handleConnectWallet = () => {
        setIsConnected(true)
        // TODO: Integrate Wagmi/Ethers.js here
        toast.success("Wallet Connected", {
            description: "Connected to Polygon Amoy Testnet",
            className: "bg-green-500/10 border-green-500/20 text-green-400"
        })
    }

    // Calculated Stability Score
    const stabilityScore = Math.max(0, 100 - (dieselTax[0] * 0.8) - (exportBan ? 40 : 0))
    const isStable = stabilityScore > 60

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col md:flex-row font-sans selection:bg-green-500/30">
            <Toaster position="top-right" theme="dark" />

            {/* Mobile Header */}
            <div className="md:hidden flex items-center justify-between p-4 glass border-b border-white/5 sticky top-0 z-50">
                <div className="flex items-center gap-2">
                    <Leaf className="h-6 w-6 text-green-400" />
                    <span className="font-bold text-lg tracking-tight">Agri-Oracle</span>
                </div>
                <Button variant="ghost" size="icon"><Menu className="h-5 w-5" /></Button>
            </div>

            {/* Sidebar */}
            <aside className="hidden md:flex flex-col w-72 glass-sidebar h-screen sticky top-0 p-6 gap-8 border-r border-white/5">
                <div className="flex items-center gap-3 px-2">
                    <div className="p-2 bg-green-500/10 rounded-lg border border-green-500/20">
                        <Leaf className="h-6 w-6 text-green-400" />
                    </div>
                    <div>
                        <h1 className="font-bold text-xl tracking-tight">Agri-Oracle</h1>
                        <p className="text-xs text-slate-400">GovTech Simulator</p>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="space-y-4">
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Policy Controls</h3>

                        <Card className="glass-card border-none bg-slate-900/50">
                            <CardHeader className="p-4 pb-2">
                                <CardTitle className="text-sm font-medium">Diesel Tax</CardTitle>
                                <CardDescription>₹{dieselTax[0]}/Litre</CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 pt-2">
                                <Slider
                                    value={dieselTax}
                                    onValueChange={setDieselTax}
                                    max={60}
                                    step={1}
                                    onValueCommit={(val) => addToHistory(`Diesel Tax Adjusted to ₹${val[0]}`, "0.002")}
                                    className="[&_.bg-primary]:bg-green-500"
                                />
                            </CardContent>
                        </Card>

                        <Card className="glass-card border-none bg-slate-900/50">
                            <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between space-y-0">
                                <div className="space-y-1">
                                    <CardTitle className="text-sm font-medium">Enact Export Ban</CardTitle>
                                    <CardDescription className={exportBan ? "text-red-400" : "text-green-400"}>
                                        {exportBan ? "Active" : "Inactive"}
                                    </CardDescription>
                                </div>
                                <Switch
                                    checked={exportBan}
                                    onCheckedChange={(c) => {
                                        setExportBan(c)
                                        addToHistory(c ? "Export Ban Enacted" : "Export Ban Lifted", "0.005")
                                        if (c) {
                                            toast.error("POLICY ALERT: Export Ban Enacted", {
                                                description: "Updating Neural Forecast... Domestic prices crashing."
                                            })
                                        } else {
                                            toast.success("Policy Update: Export Ban Lifted", {
                                                description: "Market recovery initiated."
                                            })
                                        }
                                    }}
                                    className="data-[state=checked]:bg-red-500"
                                />
                            </CardHeader>
                        </Card>
                    </div>

                    {/* Menu Items */}
                    <div className="space-y-2">
                        {/* ... existing menu items ... */}
                        <Button
                            variant="ghost"
                            onClick={() => setActiveView(activeView === 'live-feeds' ? 'dashboard' : 'live-feeds')}
                            className={`w-full justify-start gap-2 ${activeView === 'live-feeds' ? 'text-green-400 bg-green-500/10' : 'text-slate-400 hover:text-green-400 hover:bg-green-500/10'}`}
                        >
                            <Activity className="h-4 w-4" /> Live Feeds
                        </Button>
                        <Dialog open={activeView === 'supply-chain'} onOpenChange={(open) => setActiveView(open ? 'supply-chain' : 'dashboard')}>
                            <DialogTrigger asChild>
                                <Button
                                    variant="ghost"
                                    className={`w-full justify-start gap-2 ${activeView === 'supply-chain' ? 'text-green-400 bg-green-500/10' : 'text-slate-400 hover:text-green-400 hover:bg-green-500/10'}`}
                                >
                                    <Tractor className="h-4 w-4" /> Supply Chain
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="glass border-emerald-500/20 bg-slate-950/90 text-slate-50 sm:max-w-md">
                                <DialogHeader>
                                    <DialogTitle className="text-emerald-400 flex items-center gap-2">
                                        <Tractor className="h-5 w-5" /> Supply Chain Logistics
                                    </DialogTitle>
                                    <DialogDescription className="text-slate-400">
                                        Real-time tracking of agricultural produce from farm to market.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="space-y-6 py-4 relative">
                                    {/* Connecting Line */}
                                    <div className="absolute left-[19px] top-6 bottom-6 w-0.5 bg-slate-800" />

                                    {[
                                        { step: "Farm Harvest", status: "Completed", color: "bg-emerald-500", time: "Today, 06:00 AM" },
                                        { step: "Regional Storage", status: "Processing", color: "bg-blue-500", time: "Today, 10:30 AM" },
                                        { step: "Transport Logistics", status: "In Transit", color: "bg-amber-500", time: "Est. 2h" },
                                        { step: "Wholesale Market", status: "Pending", color: "bg-slate-700", time: "---" }
                                    ].map((item, i) => (
                                        <div key={i} className="relative flex items-center gap-4 z-10">
                                            <div className={`h-10 w-10 rounded-full flex items-center justify-center border-4 border-slate-950 ${item.color.replace('bg-', 'bg-').replace('500', '900/50')} ${item.status === 'Processing' || item.status === 'In Transit' ? 'animate-pulse' : ''}`}>
                                                <div className={`h-3 w-3 rounded-full ${item.color}`} />
                                            </div>
                                            <div className="flex-1 p-3 rounded-lg bg-white/5 border border-white/5">
                                                <div className="flex justify-between items-center">
                                                    <span className="font-medium text-sm">{item.step}</span>
                                                    <Badge variant="outline" className={`${item.color.replace('bg-', 'text-')} border-none bg-transparent`}>{item.status}</Badge>
                                                </div>
                                                <p className="text-xs text-slate-500 mt-1">{item.time}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </DialogContent>
                        </Dialog>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tighter bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                            AGRI-ORACLE v1.0
                        </h1>
                        <p className="text-slate-400 text-sm font-mono uppercase tracking-widest">Secure Gateway // Neural Forecast Enabled</p>
                    </div>
                    <div className="flex gap-2">
                        <Badge variant="outline" className="border-emerald-500/20 text-emerald-400 bg-emerald-500/5 gap-2 px-3 py-1">
                            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                            Network Active
                        </Badge>
                        {isConnected ? (
                            <Sheet>
                                <SheetTrigger asChild>
                                    <div className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
                                        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20 transition-colors">
                                            1,240.50 MATIC
                                        </Badge>
                                        <Button
                                            size="sm"
                                            className="bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                                        >
                                            <span className="h-2 w-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
                                            0x74a...3297
                                        </Button>
                                    </div>
                                </SheetTrigger>
                                <SheetContent className="glass border-l border-white/10 bg-slate-950/90 text-slate-50">
                                    <SheetHeader>
                                        <SheetTitle className="text-emerald-400">Wallet Overview</SheetTitle>
                                        <SheetDescription className="text-slate-400">
                                            Manage your connection to the Agri-Oracle Network.
                                        </SheetDescription>
                                    </SheetHeader>
                                    <div className="mt-8 space-y-6">
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Balance</label>
                                            <div className="flex items-baseline gap-2">
                                                <span className="text-3xl font-bold tracking-tighter text-white">1,240.50</span>
                                                <span className="text-emerald-400 font-mono">MATIC</span>
                                            </div>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Network Status</label>
                                            <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-900/20 border border-emerald-500/20">
                                                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                                                <span className="text-sm text-emerald-300">Polygon Amoy Testnet</span>
                                            </div>
                                        </div>

                                        <div className="space-y-3">
                                            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recent Activity</label>
                                            <div className="space-y-2 h-[200px] overflow-y-auto pr-2">
                                                {history.length === 0 ? (
                                                    <p className="text-sm text-slate-500 italic">No recent transactions.</p>
                                                ) : (
                                                    history.map((item, i) => (
                                                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors border border-white/5">
                                                            <div className="space-y-0.5">
                                                                <div className="text-sm font-medium">{item.action}</div>
                                                                <div className="text-xs text-slate-500">{item.time}</div>
                                                            </div>
                                                            <div className="text-xs font-mono text-red-400">-{item.cost} MATIC</div>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </SheetContent>
                            </Sheet>
                        ) : (
                            <Button
                                size="sm"
                                onClick={handleConnectWallet}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white border-none shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all hover:scale-105"
                            >
                                <Wallet className="mr-2 h-4 w-4" />
                                Connect Wallet
                            </Button>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Chart */}
                    <Card className="lg:col-span-2 glass border-slate-800 bg-slate-900/40 h-fit">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Activity className="h-5 w-5 text-green-400" />
                                Predicted Onion Prices (30 Days)
                            </CardTitle>
                            <CardDescription>AI-driven forecast based on diesel tax ({dieselTax}₹) and active bans.</CardDescription>
                        </CardHeader>
                        <CardContent className="h-[300px] w-full p-4">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={prices}>
                                    <defs>
                                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={exportBan ? "#ef4444" : "#22c55e"} stopOpacity={0.3} />
                                            <stop offset="95%" stopColor={exportBan ? "#ef4444" : "#22c55e"} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                    <XAxis dataKey="day" stroke="#64748b" tick={false} axisLine={false} />
                                    <YAxis stroke="#64748b" axisLine={false} tickLine={false} unit="₹" domain={['dataMin - 2', 'dataMax + 2']} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                                        itemStyle={{ color: exportBan ? '#f87171' : '#4ade80' }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="price"
                                        stroke={exportBan ? "#ef4444" : "#22c55e"} // Red if ban is on, green otherwise
                                        strokeWidth={2}
                                        fillOpacity={1}
                                        fill="url(#colorPrice)"
                                        animationDuration={500}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>

                    <div className="flex flex-col gap-6">
                        {/* Market Stability Index */}
                        <Card className={`glass-card border-white/5 transition-all duration-500 ${isStable ? "bg-emerald-900/10" : "bg-red-900/10 shadow-[0_0_30px_rgba(239,68,68,0.2)]"}`}>
                            <CardHeader className="pb-2">
                                <CardTitle className={`text-sm font-medium flex items-center justify-between ${isStable ? "text-emerald-400" : "text-red-400"}`}>
                                    <span>Market Stability Index</span>
                                    <Activity className="h-4 w-4" />
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-4xl font-bold tracking-tighter">{stabilityScore.toFixed(0)}</span>
                                    <span className="text-sm text-slate-500">/ 100</span>
                                </div>
                                <div className="mt-3 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full transition-all duration-1000 ${isStable ? "bg-emerald-500" : "bg-red-500 animate-pulse"}`}
                                        style={{ width: `${stabilityScore}%` }}
                                    />
                                </div>
                                <p className="mt-2 text-xs text-slate-400">
                                    {exportBan
                                        ? "CRITICAL ALERT: Export ban causing extreme market volatility."
                                        : "Market conditions are optimal for trade."}
                                </p>
                            </CardContent>
                        </Card>
                        {/* NDVI Vision - Dynamic */}
                        <Dialog>
                            <DialogTrigger asChild>
                                <Card className="glass-card border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.15)] overflow-hidden relative group bg-slate-900/60 cursor-pointer transition-all hover:scale-[1.01]">
                                    <CardHeader className="pb-2 flex flex-row items-center justify-between">
                                        <CardTitle className="flex items-center gap-2 text-sm font-bold text-emerald-400">
                                            <Box className="h-4 w-4" />
                                            SATELLITE NDVI VISION
                                        </CardTitle>
                                        <div className="flex items-center gap-2">
                                            <span className="relative flex h-2 w-2">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                                            </span>
                                            <span className="text-[10px] font-mono text-red-500 uppercase font-bold tracking-tighter">Live Feed</span>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="p-4 pt-2">
                                        <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-white/10 shadow-2xl bg-black">
                                            {/* The Moving Scan Line */}
                                            <div className="absolute inset-0 bg-[linear-gradient(transparent_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] animate-[scan_3s_linear_infinite] z-20" />

                                            {/* Dark Satellite Map Image */}
                                            <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&q=80')] bg-cover opacity-40 grayscale group-hover:grayscale-0 transition-all duration-700" />

                                            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 z-30">
                                                <div className="bg-black/60 backdrop-blur-md p-3 rounded-md border border-emerald-500/30">
                                                    <p className="text-[10px] font-mono text-emerald-500 text-center mb-2 tracking-[0.3em] font-bold">{satStatus}...</p>
                                                    <div className="grid grid-cols-2 gap-4 text-[10px] font-mono text-white">
                                                        <div className="text-center border-r border-white/10 pr-2">
                                                            <span className="block text-slate-500 text-[8px]">LATITUDE</span>
                                                            <span className="text-emerald-400">{coords.lat}</span>
                                                        </div>
                                                        <div className="text-center pl-2">
                                                            <span className="block text-slate-500 text-[8px]">LONGITUDE</span>
                                                            <span className="text-emerald-400">{coords.lng}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <Badge className="bg-emerald-500 text-black font-bold">CLICK TO INSPECT</Badge>
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </DialogTrigger>
                            <SatelliteDialog />
                        </Dialog>

                        {/* Blockchain Hashes */}
                        <Card className={`glass border-slate-800 bg-slate-900/40 flex-1 transition-all duration-300 ${isSyncing ? "border-purple-500/50 shadow-[0_0_30px_rgba(168,85,247,0.2)]" : ""}`}>
                            <CardHeader className="pb-2">
                                <CardTitle className="flex items-center gap-2 text-sm">
                                    <Box className="h-4 w-4 text-purple-400" />
                                    Polygon Chain Sync
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {initialHashes.map((hash, i) => (
                                    <div key={i} className="text-[10px] font-mono text-slate-500 bg-black/20 p-2 rounded border border-white/5 truncate hover:text-purple-400 transition-colors cursor-pointer hover:bg-black/40">
                                        {hash} <span className="float-right text-slate-600">{(i * 2)}s ago</span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </main>
            {/* Live Feeds Ticker */}
            {activeView === 'live-feeds' && (
                <div className="fixed bottom-0 left-0 right-0 h-10 bg-black/80 backdrop-blur-md border-t border-emerald-500/30 flex items-center overflow-hidden z-50">
                    <div className="bg-emerald-600 px-3 h-full flex items-center text-xs font-bold text-white uppercase tracking-wider z-10 shadow-lg">
                        Live News
                    </div>
                    <div className="flex animate-[slide_20s_linear_infinite] whitespace-nowrap gap-12 pl-4 text-xs font-mono text-emerald-400/80">
                        <span>🥬 NASHIK REGION REPORTS 15% OVERPRODUCTION OF RED ONIONS</span>
                        <span>🚜 DIESEL PRICES STABILIZING AFTER RECENT HIKES</span>
                        <span>🌩️ MONSOON DELAYS IMPACTING WESTERN MAHARASHTRA CROPS</span>
                        <span>📉 GOVT CONSIDERING EXPORT SUBSIDIES FOR POTATO FARMERS</span>
                    </div>
                </div>
            )}
        </div>
    )
}
