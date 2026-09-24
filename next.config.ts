import type { NextConfig } from "next";
import os from "node:os";
import path from "node:path";

function lanDevOrigins() {
  const hosts = new Set<string>(["127.0.0.1"]);
  for (const addresses of Object.values(os.networkInterfaces())) {
    for (const address of addresses ?? []) {
      const family = String(address.family);
      if ((family === "IPv4" || family === "4") && !address.internal) {
        hosts.add(address.address);
      }
    }
  }
  return [...hosts];
}

const nextConfig: NextConfig = {
  allowedDevOrigins: lanDevOrigins(),
  turbopack: {
    root: path.resolve(process.cwd()),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8001/api/:path*",
      },
    ];
  },
};

export default nextConfig;
