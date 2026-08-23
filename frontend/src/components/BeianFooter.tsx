/**
 * ICP and Public Security Bureau filing notices.
 *
 * A site hosted on mainland-China infrastructure must display its ICP filing number,
 * linked to beian.miit.gov.cn. Once the PSB filing (公安备案) is granted — required
 * within 30 days of the ICP filing — that number must be shown too, linked to the
 * public-security enquiry page.
 *
 * Values come from the build environment, so this renders nothing until the filings
 * actually exist. Set them in the frontend environment before `next build`:
 *
 *   NEXT_PUBLIC_ICP_NUMBER="京ICP备xxxxxxxx号-1"
 *   NEXT_PUBLIC_PSB_NUMBER="京公网安备 11010xxxxxxxxx号"
 *   NEXT_PUBLIC_PSB_CODE="11010xxxxxxxxx"      # digits only, for the enquiry link
 *   NEXT_PUBLIC_PSB_LOGO="/beian-psb.png"      # optional official badge, self-hosted
 */
export default function BeianFooter() {
  const icp = process.env.NEXT_PUBLIC_ICP_NUMBER;
  const psb = process.env.NEXT_PUBLIC_PSB_NUMBER;
  const psbCode = process.env.NEXT_PUBLIC_PSB_CODE;
  const logo = process.env.NEXT_PUBLIC_PSB_LOGO;

  if (!icp && !psb) return null;

  return (
    <footer className="w-full py-6 text-center text-xs text-charcoal/50">
      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
        {icp && (
          <a
            href="https://beian.miit.gov.cn"
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent"
          >
            {icp}
          </a>
        )}
        {psb && (
          <a
            href={
              psbCode
                ? `https://beian.mps.gov.cn/#/query/webSearch?code=${psbCode}`
                : "https://beian.mps.gov.cn"
            }
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 hover:text-accent"
          >
            {/* The bureau supplies an official badge image. Save it to
                frontend/public/ and point NEXT_PUBLIC_PSB_LOGO at it (e.g.
                "/beian-psb.png"); the text link alone is fine until then. Self-hosted,
                never hotlinked — Principle I forbids external asset hosts. */}
            {logo && <img src={logo} alt="" width={14} height={14} />}
            {psb}
          </a>
        )}
      </div>
    </footer>
  );
}
