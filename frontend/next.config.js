/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Media is served from object storage; use plain <img>, no next/image domains needed.
  eslint: { ignoreDuringBuilds: true },
};

module.exports = nextConfig;
