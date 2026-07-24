const ALLOWED_ORIGINS=(process.env.ALLOWED_PORTFOLIO_ORIGINS||'').split(',').map(value=>value.trim()).filter(Boolean);

export default async function handler(request,response){
  if(request.method!=='POST')return response.status(405).json({error:'method_not_allowed'});
  const origin=request.headers.origin||'';
  if(!ALLOWED_ORIGINS.includes(origin))return response.status(403).json({error:'origin_not_allowed'});
  if(request.headers['content-type']?.split(';')[0]!=='application/json')return response.status(415).json({error:'unsupported_media_type'});
  const phone=process.env.LUCA_PHONE_E164;
  if(!phone||!/^\+[1-9]\d{7,14}$/.test(phone))return response.status(503).json({error:'contact_unavailable'});
  response.setHeader('Cache-Control','no-store, max-age=0');
  response.setHeader('Content-Type','application/json; charset=utf-8');
  response.setHeader('Vary','Origin');
  return response.status(200).json({tel:`tel:${phone}`});
}

/*
Deployment requirements outside this example handler:
- store LUCA_PHONE_E164 and ALLOWED_PORTFOLIO_ORIGINS as platform environment variables;
- apply provider-level IP rate limiting to POST /api/contact/call;
- require a managed bot challenge before the request where appropriate;
- exclude response bodies and environment values from analytics and request logging;
- deploy only over HTTPS with the response headers documented in ../../_headers.
*/
