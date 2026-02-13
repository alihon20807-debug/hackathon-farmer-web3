import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Signal, Crosshair, Cpu } from "lucide-react";

export function SatelliteDialog() {
    return (
        <DialogContent className="max-w-[95vw] w-[1200px] h-[80vh] bg-slate-950/95 border-emerald-500/20 glass p-0 overflow-hidden flex flex-col">
            <DialogHeader className="p-6 border-b border-white/5 flex flex-row items-center justify-between space-y-0">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-emerald-500/10 rounded border border-emerald-500/20">
                        <Signal className="h-5 w-5 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                    </div>
                    <div>
                        <DialogTitle className="text-xl font-bold tracking-tighter text-emerald-400 hud-glow">
                            ORACLE-01: FIELD TELEMETRY
                        </DialogTitle>
                        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 uppercase tracking-widest mt-1">
                            <span className="flex items-center gap-1">
                                <Crosshair className="h-3 w-3" /> 19.07° N, 72.87° E
                            </span>
                            <span className="text-emerald-500/50">|</span>
                            <span className="flex items-center gap-1 text-red-500 animate-blink font-bold">
                                LIVE FEED
                            </span>
                        </div>
                    </div>
                </div>
            </DialogHeader>
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: The View */}
                <div className="flex-[2] relative bg-black flex items-center justify-center overflow-hidden border-r border-white/5 p-4">
                    <TransformWrapper
                        initialScale={1}
                        initialPositionX={0}
                        initialPositionY={0}
                    >
                        <TransformComponent wrapperClass="!w-full !h-full" contentClass="!w-full !h-full flex items-center justify-center">
                            <div className="relative w-full h-full shadow-[0_0_50px_rgba(0,0,0,0.5)] rounded-lg overflow-hidden border border-white/5">
                                <img
                                    src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&q=80"
                                    alt="Satellite View"
                                    className="w-full h-full object-cover transition-all duration-700"
                                    style={{
                                        filter: 'contrast(1.1) brightness(1.05)'
                                    }}
                                />
                            </div>
                        </TransformComponent>
                    </TransformWrapper>
                </div>

                {/* Right Panel: The Intel */}
                <aside className="w-80 bg-slate-900/90 backdrop-blur-xl border-l border-white/5 p-6 flex flex-col gap-8 overflow-y-auto relative">
                    <div className="relative z-10 flex flex-col gap-8 h-full">
                        {/* Sensor Stats */}
                        <div className="space-y-4">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                                <Cpu className="h-3 w-3" /> Sensor Configuration
                            </h3>
                            <div className="space-y-3">
                                {[
                                    { label: "SATELLITE", value: "Sentinel-2 L2A" },
                                    { label: "RESOLUTION", value: "10m / Pixel" },
                                    { label: "CLOUD_COVER", value: "8.4%" },
                                    { label: "SENSOR_ID", value: "MSI_RX9-X" }
                                ].map((stat, i) => (
                                    <div key={i} className="flex justify-between items-center border-b border-white/5 pb-2 transition-all hover:bg-white/5 px-1">
                                        <span className="text-[10px] font-mono text-slate-500 uppercase">{stat.label}</span>
                                        <span className="text-[11px] font-mono text-emerald-400 font-bold">{stat.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Natural Legend */}
                        <div className="space-y-4">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Vegetation Key</h3>
                            <div className="space-y-3">
                                {[
                                    { color: "bg-emerald-700", label: "Healthy Crops" },
                                    { color: "bg-yellow-500", label: "Maturing Crops" },
                                    { color: "bg-[#d2b48c]", label: "Bare Soil / Harvested" }
                                ].map((item, i) => (
                                    <div key={i} className="flex items-center gap-3">
                                        <div className={`h-3 w-3 rounded-sm ${item.color} border border-white/10 shadow-sm`} />
                                        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-tight">{item.label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* AI Observation */}
                        <div className="space-y-4">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Neural Inference</h3>
                            <Card className="bg-white/5 border-white/10 p-4 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-1 opacity-20">
                                    <Signal className="h-8 w-8 text-emerald-500" />
                                </div>
                                <p className="text-xs text-slate-300 leading-relaxed font-mono italic">
                                    "Neural Analysis suggests <span className="text-emerald-400 font-bold">92% yield probability</span> in the northern quadrants. Biomass density indicates optimal water retention."
                                </p>
                                <div className="mt-4 flex items-center gap-2">
                                    <Badge variant="outline" className="text-[9px] border-emerald-500/30 text-emerald-400 bg-transparent uppercase">Model: Agri-Gen-3</Badge>
                                    <div className="flex-1 h-px bg-white/10" />
                                </div>
                            </Card>
                        </div>

                        <div className="mt-auto pt-4 border-t border-white/5 space-y-3">
                            <Button className="w-full bg-emerald-600/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-600/20 transition-all font-mono text-xs tracking-tighter">
                                DOWNLOAD SPECTRAL DATA (.TIFF)
                            </Button>
                        </div>
                    </div>
                </aside>
            </div>
        </DialogContent>
    );
}
