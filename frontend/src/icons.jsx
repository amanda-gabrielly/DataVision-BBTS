const P = {
  home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',
  chat: 'M21 12a8 8 0 01-11.5 7.2L3 21l1.8-5.5A8 8 0 1121 12z',
  folder: 'M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V6z',
  chart: 'M4 20V10m6 10V4m6 16v-7m5 7H3',
  flag: 'M5 21V4m0 0h11l-2 4 2 4H5',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zm-8 9a8 8 0 0116 0',
  upload: 'M12 16V4m0 0l-4 4m4-4l4 4M4 20h16',
  search: 'M11 19a8 8 0 100-16 8 8 0 000 16zm10 2l-4.3-4.3',
  x: 'M6 6l12 12M18 6L6 18',
  file: 'M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5zm0 0v5h5',
  check: 'M5 12l5 5 9-10',
  alert: 'M12 9v4m0 4h.01M10.3 3.9L2.4 18a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  tree: 'M12 5v6m0 0H6v4m6-4h6v4M12 3h.01M6 17h.01M18 17h.01',
  flow: 'M4 4h6v5H4zM14 15h6v5h-6zM7 9v3a2 2 0 002 2h5',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  table: 'M3 5h18v14H3zM3 10h18M9 5v14',
  info: 'M12 8h.01M11 12h1v5h1M12 21a9 9 0 100-18 9 9 0 000 18z',
  back: 'M15 6l-6 6 6 6',
  arrow: 'M5 12h14m-6-6l6 6-6 6',
  sun: 'M12 16a4 4 0 100-8 4 4 0 000 8zM12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5',
  moon: 'M21 13A9 9 0 1111 3a7 7 0 0010 10z',
  layers: 'M12 3l9 5-9 5-9-5 9-5zm-9 9l9 5 9-5M3 16l9 5 9-5',
  camera: 'M4 8h3l2-3h6l2 3h3v11H4V8zm8 9a3.5 3.5 0 100-7 3.5 3.5 0 000 7z',
}
export function Ic({ n, s = 20, ...rest }) {
  return (
    <svg className="ic" width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      <path d={P[n] || P.file} />
    </svg>
  )
}
export function FolderArt({ color }) {
  return (
    <svg className="fo" viewBox="0 0 72 60" aria-hidden="true">
      <path d="M4 12a6 6 0 016-6h16l6 7h26a6 6 0 016 6v30a6 6 0 01-6 6H10a6 6 0 01-6-6V12z" fill={color} opacity=".55" />
      <path d="M4 22a6 6 0 016-6h52a6 6 0 016 6v28a6 6 0 01-6 6H10a6 6 0 01-6-6V22z" fill={color} />
    </svg>
  )
}
