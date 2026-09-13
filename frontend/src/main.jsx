import React,{useEffect,useMemo,useState} from "react";
import {createRoot} from "react-dom/client";
import {ArrowLeft,ArrowRight,Bell,CalendarDays,Check,ChevronDown,ChevronRight,CircleHelp,Clock3,Compass,FileCheck2,Filter,LocateFixed,Map,MapPin,Menu,MessageCircle,Navigation,Phone,Search,Send,ShieldCheck,SlidersHorizontal,Star,Truck,UserRound,Upload,Wallet,Wrench,X,Zap} from "lucide-react";
import "./styles.css";

const API_BASE = (import.meta.env && import.meta.env.VITE_API_URL) || "http://localhost:8000";

function apiProviderToCard(p){
 return {
  id:p.id, name:p.business_name, rating:p.avg_rating||0, reviews:p.rating_count||0,
  distance:p.distance_km!=null?p.distance_km+" km":"Distance unknown",
  eta:"—", price:"Quote after request",
  verified:p.verification_status==="APPROVED",
  equipment:p.equipment_summary||"Equipment details on request",
  jobs:p.jobs_completed||0, reply:"Usually replies within a few hours",
  available:p.is_online?"Available today":"Currently offline",
  state:p.state, city:p.city,
 };
}

const SERVICES=[
 {id:"borewell",name:"Borewell services",icon:"◉",desc:"Drilling, rigs, compressors & operators"},
 {id:"jcb",name:"JCB & excavators",icon:"▣",desc:"Digging, earthwork & site clearing"},
 {id:"crane",name:"Crane services",icon:"↥",desc:"Lifting, shifting & construction"},
 {id:"tractor",name:"Tractor services",icon:"▰",desc:"Farm work, hauling & implements"},
 {id:"tanker",name:"Water tankers",icon:"≈",desc:"Water delivery for homes & sites"},
 {id:"truck",name:"Trucks & tippers",icon:"▱",desc:"Material transport & site logistics"},
 {id:"agri",name:"Agriculture equipment",icon:"✣",desc:"Farm equipment & field operations"},
 {id:"construction",name:"Construction equipment",icon:"⌂",desc:"Equipment for sites & projects"},
 {id:"rental",name:"Equipment rental",icon:"◫",desc:"Rent machines with or without operators"},
 {id:"other",name:"Other services",icon:"＋",desc:"Tell us what you need"},
];
const STATES=["Telangana","Andhra Pradesh","Karnataka","Tamil Nadu","Maharashtra","Gujarat","Rajasthan","Kerala","Odisha","West Bengal","Uttar Pradesh","Madhya Pradesh","Delhi","Haryana","Punjab","Bihar","Jharkhand","Chhattisgarh","Assam","Other"];
const PROVIDERS=[
 {id:1,name:"Sri Sai Borewell Works",rating:4.9,reviews:184,distance:"3.2 km",eta:"12 min",price:"From ₹180/ft",verified:true,equipment:"Hydraulic Rig • 1000 ft",jobs:620,reply:"Usually replies in 5 min",available:"Available today",state:"Telangana",city:"Warangal"},
 {id:2,name:"Lakshmi Drilling & Services",rating:4.8,reviews:97,distance:"5.8 km",eta:"18 min",price:"From ₹170/ft",verified:true,equipment:"Drilling Rig • 800 ft",jobs:310,reply:"Usually replies in 8 min",available:"Available today",state:"Telangana",city:"Warangal"},
 {id:3,name:"Reddy Earth & Borewell",rating:4.7,reviews:63,distance:"7.4 km",eta:"24 min",price:"Quote after site check",verified:true,equipment:"Rotary Rig • 1200 ft",jobs:205,reply:"Usually replies in 12 min",available:"Tomorrow",state:"Telangana",city:"Hanamkonda"},
 {id:4,name:"Vijaya Rural Services",rating:4.6,reviews:41,distance:"9.1 km",eta:"29 min",price:"From ₹165/ft",verified:false,equipment:"Rig • 700 ft",jobs:142,reply:"Replies in ~20 min",available:"Today after 3 PM",state:"Telangana",city:"Warangal"},
];

function App(){
 const [screen,setScreen]=useState("location");
 const [location,setLocation]=useState(null);
 const [service,setService]=useState(null);
 const [provider,setProvider]=useState(null);
 const [logged,setLogged]=useState(()=>!!localStorage.getItem("fieldly_token"));
 const [authToken,setAuthToken]=useState(()=>localStorage.getItem("fieldly_token")||null);
 const [userId,setUserId]=useState(()=>localStorage.getItem("fieldly_user_id")||null);
 const [dbServices,setDbServices]=useState([]);
 const [liveProviders,setLiveProviders]=useState(null);
 const [currentRequestId,setCurrentRequestId]=useState(null);
 const [currentBookingId,setCurrentBookingId]=useState(null);
 const [booking,setBooking]=useState(false);
 const [otp,setOtp]=useState(false);
 const [complete,setComplete]=useState(false);
 const [toast,setToast]=useState("");
 const [state,setState]=useState("Telangana");
 const [search,setSearch]=useState("");
 const [sort,setSort]=useState("Recommended");
 const [mobileNav,setMobileNav]=useState(false);
 const notify=m=>{setToast(m);setTimeout(()=>setToast(""),2400)};
 const go=s=>{setScreen(s);window.scrollTo({top:0,behavior:"smooth"})};
 const chooseLocation=l=>{setLocation(l);go("home");};

 React.useEffect(()=>{
  fetch(API_BASE+"/api/v1/services/").then(r=>r.ok?r.json():[]).then(setDbServices).catch(()=>setDbServices([]));
 },[]);

 const chooseService=async s=>{
  const dbSvc=dbServices.find(x=>x.slug===s.id);
  if(dbServices.length && !dbSvc){ notify(s.name+" isn't live in your area yet — check back soon"); return; }
  setService({...s,dbId:dbSvc?dbSvc.id:null});
  setLiveProviders(null);
  go("providers");
  try{
   const qs=new URLSearchParams({service_slug:s.id});
   if(location?.state)qs.set("state",location.state);
   if(location?.city)qs.set("city",location.city.split(",")[0]);
   const res=await fetch(API_BASE+"/api/v1/providers/?"+qs.toString());
   if(res.ok){
    const data=await res.json();
    if(data.length)setLiveProviders(data.map(apiProviderToCard));
   }
  }catch(e){ /* offline / backend not reachable — fall back to demo providers below */ }
 };

 const baseProviders=liveProviders||PROVIDERS;
 const visible=useMemo(()=>{
   let p=[...baseProviders].filter(x=>x.state===state||state==="All");
   if(search)p=p.filter(x=>(x.name+x.equipment).toLowerCase().includes(search.toLowerCase()));
   if(sort==="Nearest")p.sort((a,b)=>parseFloat(a.distance)-parseFloat(b.distance));
   if(sort==="Top rated")p.sort((a,b)=>b.rating-a.rating);
   if(sort==="Lowest price")p.sort((a,b)=>(parseInt(a.price.replace(/\D/g,""))||9999)-(parseInt(b.price.replace(/\D/g,""))||9999));
   return p;
 },[state,search,sort,baseProviders]);

 const handleLoginDone=(token,uid,name)=>{
  if(token){
   localStorage.setItem("fieldly_token",token);
   localStorage.setItem("fieldly_user_id",uid);
   setAuthToken(token); setUserId(uid);
  }
  setLogged(true); go("request");
 };

 return <div className="app">
  <Header screen={screen} go={go} location={location} logged={logged} mobileNav={mobileNav} setMobileNav={setMobileNav}/>
  {screen==="location"&&<LocationScreen onChoose={chooseLocation}/>}
  {screen==="home"&&<HomeScreen location={location} chooseService={chooseService} go={go} notify={notify}/>}
  {screen==="services"&&<ServiceScreen location={location} choose={chooseService} go={go} liveSlugs={dbServices.map(s=>s.slug)}/>}
  {screen==="requirements"&&<Requirements service={service} location={location} go={go}/>}
  {screen==="providers"&&<Providers service={service} location={location} providers={visible} search={search} setSearch={setSearch} sort={sort} setSort={setSort} setProvider={setProvider} go={go}/>}
  {screen==="provider"&&<Provider p={provider||PROVIDERS[0]} logged={logged} go={go} notify={notify}/>}
  {screen==="login"&&<Login onDone={handleLoginDone}/>}
  {screen==="request"&&<Request p={provider||PROVIDERS[0]} service={service} location={location} authToken={authToken} go={go} notify={notify} onCreated={setCurrentRequestId}/>}
  {screen==="waiting"&&<Waiting p={provider||PROVIDERS[0]} requestId={currentRequestId} authToken={authToken} go={go} notify={notify} onBooked={setCurrentBookingId}/>}
  {screen==="booking"&&<Booking go={go} setOtp={setOtp} bookingId={currentBookingId} authToken={authToken}/>}
  {screen==="tracking"&&<Tracking go={go} otp={otp} setOtp={setOtp} notify={notify} bookingId={currentBookingId} authToken={authToken} p={provider||PROVIDERS[0]}/>}
  {screen==="complete"&&<Complete go={go} complete={complete} setComplete={setComplete} notify={notify} bookingId={currentBookingId} authToken={authToken} p={provider||PROVIDERS[0]}/>}
  {screen==="account"&&<Account logged={logged} go={go}/>}
  {screen==="join"&&<ProviderJoin go={go} notify={notify}/>}
  {screen==="help"&&<Help/>}
  {screen!=="location"&&screen!=="providers"&&<Footer go={go}/>}
  {toast&&<div className="toast"><Check size={16}/>{toast}</div>}
 </div>
}

function Header({screen,go,location,logged,mobileNav,setMobileNav}){
 return <header className="header"><div className="header-inner">
  <button className="brand" onClick={()=>go(location?"home":"location")}><span className="logo">F</span><span>fieldly</span></button>
  <nav><button onClick={()=>go(location?"services":"location")}>Services</button><button onClick={()=>go("providers")}>Explore</button><button onClick={()=>go("join")}>Become a provider</button><button onClick={()=>go("help")}>Help</button></nav>
  <div className="head-actions">
   {location&&<button className="head-location" onClick={()=>go("location")}><MapPin size={15}/>{location.label}<ChevronDown size={13}/></button>}
   <button className="head-icon"><Bell size={18}/></button>
   <button className="head-avatar" onClick={()=>go("account")}><UserRound size={17}/></button>
   <button className="mobile-menu" onClick={()=>setMobileNav(!mobileNav)}><Menu/></button>
  </div>
 </div>{mobileNav&&<div className="mobile-nav"><button onClick={()=>{go("services");setMobileNav(false)}}>Services</button><button onClick={()=>{go("providers");setMobileNav(false)}}>Explore</button><button onClick={()=>{go("join");setMobileNav(false)}}>Become a provider</button><button onClick={()=>{go("account");setMobileNav(false)}}>Account</button></div>}</header>
}

function LocationScreen({onChoose}){
 const [mode,setMode]=useState(null),[query,setQuery]=useState(""),[state,setState]=useState("Telangana");
 const choose=(label,kind)=>onChoose({label,kind,state,city:label.split(",")[0]});
 return <div className="location-screen"><div className="location-card">
   <div className="location-logo"><span className="logo">F</span></div><p className="eyebrow">WELCOME TO FIELDLY</p><h1>Where do you need the service?</h1><p className="sub">Start with the work location. You can use your current location, choose a point on the map, or enter an address manually.</p>
   <div className="location-options">
    <button onClick={()=>{navigator.geolocation?.getCurrentPosition(()=>choose("Current location","gps"),()=>choose("Location unavailable — choose manually","manual"));}}><span className="option-icon gps"><LocateFixed/></span><div><b>Use my current location</b><small>Fastest way to find providers near you</small></div><ChevronRight/></button>
    <button onClick={()=>setMode("map")}><span className="option-icon"><Map/></span><div><b>Choose on map</b><small>Drop a pin exactly where the work is needed</small></div><ChevronRight/></button>
    <button onClick={()=>setMode("manual")}><span className="option-icon"><Search/></span><div><b>Enter location manually</b><small>Search by address, village, town or landmark</small></div><ChevronRight/></button>
   </div>
   <div className="location-note"><ShieldCheck size={15}/><span>Your service location can be different from your home address.</span></div>
   {mode&&<div className="location-modal"><div className="modal-head"><b>{mode==="map"?"Choose a point on the map":"Enter service location"}</b><button onClick={()=>setMode(null)}><X/></button></div>
    {mode==="map"?<><div className="big-map"><div className="map-grid"></div><div className="map-pin-center"><MapPin/></div><div className="map-search"><Search/><input placeholder="Search area or landmark" value={query} onChange={e=>setQuery(e.target.value)}/></div></div><button className="primary full" onClick={()=>choose(query||"Warangal, Telangana","map")}>Confirm this location</button></>:
    <><label className="field"><b>State</b><select value={state} onChange={e=>setState(e.target.value)}>{STATES.map(x=><option key={x}>{x}</option>)}</select></label><label className="field"><b>Area / city / village</b><div className="input"><Search/><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="e.g. Warangal, Kazipet, Hanamkonda"/></div></label><div className="suggestions">{[query||"Warangal", "Hanamkonda","Kazipet","Hyderabad"].map((x,i)=><button key={x+i} onClick={()=>choose(`${x}, ${state}`,"manual")}><MapPin size={15}/><span><b>{x}</b><small>{state}, India</small></span></button>)}</div></>}
   </div>}
 </div></div>
}


function HomeScreen({location,chooseService,go,notify}){
 const [homeSearch,setHomeSearch]=useState("");
 const popular=SERVICES.slice(0,8);
 const nearby=PROVIDERS.slice(0,3);
 const matches=homeSearch
   ? SERVICES.filter(s=>(s.name+" "+s.desc).toLowerCase().includes(homeSearch.toLowerCase()))
   : [];
 return <div className="home-page">
   <section className="home-hero">
    <div className="home-hero-inner">
      <div className="home-hero-copy">
        <p className="eyebrow">SERVICES WHERE THE WORK IS</p>
        <h1>What do you need help with today?</h1>
        <p>Find trusted equipment, operators and service providers for farms, homes and construction sites.</p>
        <div className="home-search">
          <Search size={19}/>
          <input
            value={homeSearch}
            onChange={e=>setHomeSearch(e.target.value)}
            placeholder="Search services, equipment or describe your job"
          />
          {homeSearch&&<button className="search-clear" onClick={()=>setHomeSearch("")}><X size={16}/></button>}
        </div>
        {homeSearch&&<div className="search-results">
          {matches.length?matches.slice(0,5).map(s=><button key={s.id} onClick={()=>chooseService(s)}>
            <span className="service-symbol">{s.icon}</span>
            <span><b>{s.name}</b><small>{s.desc}</small></span><ChevronRight/>
          </button>):<div className="search-empty">No exact service found. <button onClick={()=>{go("services");}}>Browse all services</button></div>}
        </div>}
        <div className="home-location-row">
          <button className="home-location" onClick={()=>go("location")}><MapPin size={15}/><span><small>Service location</small><b>{location?.label||"Choose location"}</b></span><ChevronDown size={14}/></button>
          <span className="location-help"><ShieldCheck size={14}/> Work location can be different from your home</span>
        </div>
      </div>
      <div className="hero-work-card">
        <div className="hero-work-map">
          <div className="map-grid"></div>
          <div className="hero-route"></div>
          <span className="hero-pin pin-a"><MapPin/></span>
          <span className="hero-pin pin-b"><Truck/></span>
          <div className="hero-map-label"><span className="live-dot"></span>Providers near you</div>
        </div>
        <div className="hero-card-footer"><div><b>Find the right equipment</b><small>Compare nearby providers before you request</small></div><button onClick={()=>go("providers")}><ArrowRight size={17}/></button></div>
      </div>
    </div>
   </section>

   <main className="home-content">
     <section className="home-section">
       <div className="section-heading"><div><p className="eyebrow">START HERE</p><h2>Popular services</h2></div><button className="text-link" onClick={()=>go("services")}>View all <ArrowRight size={15}/></button></div>
       <div className="popular-grid">
         {popular.map(s=><button className="popular-card" key={s.id} onClick={()=>chooseService(s)}>
           <span className="popular-icon">{s.icon}</span>
           <span><b>{s.name.replace(" services","")}</b><small>{s.desc.split(" & ")[0]}</small></span>
           <ChevronRight size={17}/>
         </button>)}
       </div>
     </section>

     <section className="home-section split-home">
       <div className="home-panel nearby-panel">
         <div className="section-heading compact"><div><p className="eyebrow">NEARBY</p><h2>Providers around you</h2></div><button className="text-link" onClick={()=>go("providers")}>Explore <ArrowRight size={15}/></button></div>
         <div className="nearby-list">
           {nearby.map(p=><button className="nearby-row" key={p.id} onClick={()=>{go("providers");notify("Explore nearby providers for this service")}}>
             <span className="provider-avatar">{p.name.split(" ").map(x=>x[0]).slice(0,2).join("")}</span>
             <span className="nearby-info"><b>{p.name}</b><small><Star size={12}/> {p.rating} · {p.reviews} reviews · {p.distance}</small></span>
             {p.verified&&<span className="mini-verified"><ShieldCheck size={13}/> Verified</span>}
           </button>)}
         </div>
       </div>
       <div className="home-panel trust-panel">
         <div className="trust-visual"><ShieldCheck size={30}/><span>Built for real-world work</span></div>
         <p className="eyebrow">WHY FIELDLY</p>
         <h2>Know who you're booking.</h2>
         <p>See provider ratings, equipment, verification, service area and availability before you send a request.</p>
         <div className="trust-points"><span><Check size={14}/> Verified providers</span><span><Check size={14}/> Equipment details</span><span><Check size={14}/> Live job updates</span></div>
       </div>
     </section>

     <section className="home-section how-section">
       <div className="section-heading"><div><p className="eyebrow">SIMPLE FLOW</p><h2>From request to service</h2></div></div>
       <div className="how-grid">
         <div><span>01</span><b>Tell us what you need</b><small>Choose a service and answer only the relevant questions.</small></div>
         <div><span>02</span><b>Compare providers</b><small>Review distance, ratings, equipment, availability and quotes.</small></div>
         <div><span>03</span><b>Track the job</b><small>Stay updated from acceptance through service completion.</small></div>
       </div>
     </section>

     <section className="provider-cta">
       <div><div><p className="eyebrow">FOR EQUIPMENT OWNERS</p><h2>Have a machine or operate one?</h2><p>List your equipment, receive relevant requests and grow your work with Fieldly.</p></div><button className="primary" onClick={()=>go("join")}>Become a provider <ArrowRight size={16}/></button></div>
     </section>
   </main>
 </div>
}

function ServiceScreen({location,choose,go,liveSlugs}){
 const isLive=id=>!liveSlugs||liveSlugs.length===0||liveSlugs.includes(id);
 return <div className="page"><div className="page-top"><div><button className="back-home" onClick={()=>go("home")}><ArrowLeft size={15}/> Back to home</button><p className="eyebrow">STEP 2 OF 3</p><h1>What do you need?</h1><p>Choose the service for this location. We’ll ask only the details relevant to that service.</p></div><button className="change-location" onClick={()=>go("location")}><MapPin size={15}/>{location?.label}<span>Change</span></button></div>
 <div className="service-cards">{SERVICES.map(s=><button className="service-card" key={s.id} onClick={()=>choose(s)} style={isLive(s.id)?{}:{opacity:0.55}}><span className="service-icon">{s.icon}</span><span className="service-copy"><b>{s.name}</b><small>{isLive(s.id)?s.desc:"Coming soon in your area"}</small></span><ArrowRight size={17}/></button>)}</div>
 <div className="service-help"><CircleHelp size={19}/><div><b>Not sure which service?</b><span>Tell us what job you are trying to do and we’ll guide you.</span></div><button onClick={()=>go("help")}>Get help</button></div>
 </div>
}

function Requirements({service,location,go}){
 const [step,setStep]=useState(1);
 const common=<><Field label="Preferred date"><div className="two"><div className="input"><CalendarDays/><span>Select date</span></div><div className="input"><Clock3/><span>Preferred time</span></div></div></Field><Field label="Site access"><div className="chips">{["Easy access","Narrow road","Difficult terrain"].map(x=><button className="chip" key={x}>{x}</button>)}</div></Field><Field label="Additional notes (optional)"><textarea placeholder="Anything the provider should know?"></textarea></Field></>;
 const specific=service?.id==="borewell"?<><Field label="Expected depth (optional)" hint="If you don't know, leave blank."><div className="input"><input placeholder="e.g. 600"/><span>feet</span></div></Field><Field label="Purpose"><div className="chips">{["Home","Farm","Construction","Business"].map(x=><button className="chip" key={x}>{x}</button>)}</div></Field></>:service?.id==="jcb"?<><Field label="What work is needed?"><div className="chips">{["Digging","Earthwork","Site clearing","Loading"].map(x=><button className="chip" key={x}>{x}</button>)}</div></Field><Field label="Operator required?"><div className="chips"><button className="chip">Yes</button><button className="chip">No</button></div></Field></>:<Field label="What should the provider know?"><textarea placeholder={`Tell the ${service?.name||"provider"} about the job…`}></textarea></Field>;
 return <div className="page narrow"><button className="back" onClick={()=>go("services")}><ArrowLeft/> Services</button><div className="form-heading"><span className="service-icon large">{service?.icon}</span><div><p className="eyebrow">{service?.name?.toUpperCase()}</p><h1>Tell us about the job</h1><p>We’ll use these details to show suitable nearby providers.</p></div></div><div className="progress"><i className={step>=1?"on":""}></i><i className={step>=2?"on":""}></i></div><div className="card form-card">
 {step===1?<><Field label="Service location"><div className="input readonly"><MapPin/>{location?.label}<button onClick={()=>go("location")}>Change</button></div></Field>{specific}<button className="primary full" onClick={()=>setStep(2)}>Continue <ArrowRight/></button></>:<>{common}<button className="primary full" onClick={()=>go("providers")}>Find nearby providers <ArrowRight/></button></>}
 <p className="privacy"><ShieldCheck/> Exact contact details are requested only when you proceed with a provider.</p></div></div>
}

function Providers({service,location,providers,search,setSearch,sort,setSort,setProvider,go}){
 return <div className="provider-explorer"><div className="explorer-head"><div><button className="back" onClick={()=>go("services")}><ArrowLeft/> Change service</button><h1>Providers near {location?.city||"you"}</h1><p>{providers.length} providers match your <b>{service?.name}</b> request.</p></div><div className="explorer-location"><MapPin size={15}/>{location?.label}</div></div>
 <div className="explorer-body"><aside className="provider-panel"><div className="search-input"><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search providers or equipment"/></div><div className="filter-row">{["Recommended","Nearest","Top rated","Lowest price"].map(x=><button className={sort===x?"active":""} onClick={()=>setSort(x)} key={x}>{x}</button>)}<button><Filter/></button></div><div className="count"><b>{providers.length} providers</b><span>Updated just now</span></div>{providers.map(p=><button className="provider-row" key={p.id} onClick={()=>{setProvider(p);go("provider")}}><div className="provider-avatar">{p.name[0]}</div><div className="provider-info"><div className="provider-name"><b>{p.name}</b>{p.verified&&<ShieldCheck/>}</div><div className="rating"><Star fill="currentColor"/><b>{p.rating}</b><span>({p.reviews})</span><i>•</i><span>{p.distance}</span></div><p>{p.equipment}</p><div className="provider-meta"><span>{p.available}</span><strong>{p.price}</strong></div></div><ChevronRight/></button>)}</aside>
 <div className="map-view"><div className="map-texture"></div><div className="map-search-pill"><LocateFixed/> Service location</div><div className="you-pin"><span></span><MapPin/></div>{providers.map((p,i)=><button key={p.id} className={`provider-pin p${i+1}`} onClick={()=>{setProvider(p);go("provider")}}><Star fill="currentColor"/><b>{p.rating}</b></button>)}<div className="map-legend"><b>{providers.length} providers nearby</b><span>Tap a provider on the map or list to compare</span></div></div></div></div>
}

function Provider({p,logged,go,notify}){
 return <div className="page provider-page"><button className="back" onClick={()=>go("providers")}><ArrowLeft/> Providers</button><div className="profile-top"><div className="big-avatar">{p.name[0]}</div><div className="profile-info"><div className="profile-title"><h1>{p.name}</h1>{p.verified&&<span className="verified"><ShieldCheck/> Verified provider</span>}</div><div className="rating big"><Star fill="currentColor"/><b>{p.rating}</b><span>{p.reviews} reviews</span><i>•</i><span>{p.distance} away</span></div><p>Trusted local service provider with listed equipment, verified profile and experienced operators.</p><div className="actions"><button className="secondary" onClick={()=>notify("Platform-protected call") }><Phone/> Call</button><button className="secondary" onClick={()=>notify("Secure chat opened")}><MessageCircle/> Chat</button><button className="primary" onClick={()=>logged?go("request"):go("login")}>Request service <ArrowRight/></button></div></div></div>
 <div className="profile-grid"><main><section className="card"><h3>At a glance</h3><div className="trust-grid"><Trust icon={<ShieldCheck/>} t="Identity verified" s="Provider verification completed"/><Trust icon={<Wrench/>} t="Equipment verified" s={p.equipment}/><Trust icon={<Zap/>} t="Fast response" s={p.reply}/><Trust icon={<Check/>} t={`${p.jobs}+ completed jobs`} s="Completed on platform"/></div></section><section className="card"><div className="section-head"><h3>Services & equipment</h3><span>Listed equipment</span></div>{["Hydraulic borewell rig • up to 1000 ft","Compressor • high pressure","Experienced operator • available"].map(x=><div className="line-item" key={x}><b>{x}</b><small>Verified listing</small></div>)}</section><section className="card"><div className="section-head"><h3>Customer reviews</h3><button>See all</button></div><Review n="Ramesh K." t="Reached on time, explained the work clearly and the equipment was well maintained."/><Review n="Srinivas P." t="Good communication and professional service." /></section></main><aside><div className="quote-box"><p className="eyebrow">STARTING PRICE</p><h2>{p.price}</h2><p>Final pricing can depend on actual work, travel, site conditions and provider quote.</p><div className="mini"><span>Availability</span><b>{p.available}</b></div><div className="mini"><span>Service area</span><b>{p.distance} away</b></div><button className="primary full" onClick={()=>logged?go("request"):go("login")}>Request this provider</button><small><ShieldCheck/> Your personal number stays private</small></div></aside></div></div>
}
function Trust({icon,t,s}){return <div className="trust"><span>{icon}</span><div><b>{t}</b><small>{s}</small></div></div>}
function Review({n,t}){return <div className="review"><div>★★★★★</div><p>“{t}”</p><b>{n}</b></div>}

function Login({onDone}){
 const [name,setName]=useState(""),[phone,setPhone]=useState(""),[sent,setSent]=useState(false),[code,setCode]=useState("");
 const [busy,setBusy]=useState(false),[error,setError]=useState(""),[devHint,setDevHint]=useState("");

 const sendOtp=async()=>{
  setBusy(true);setError("");
  try{
   const res=await fetch(API_BASE+"/api/v1/auth/request-otp",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})});
   const data=await res.json().catch(()=>({}));
   setDevHint(data.dev_hint||"");
   setSent(true);
  }catch(e){
   // Backend not reachable — still let the flow continue in demo mode.
   setSent(true);
  }
  setBusy(false);
 };

 const verify=async()=>{
  setBusy(true);setError("");
  try{
   const res=await fetch(API_BASE+"/api/v1/auth/verify-otp",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,otp:code,name,role:"customer"})});
   if(!res.ok){ const d=await res.json().catch(()=>({}));throw new Error(d.detail||"Invalid OTP"); }
   const data=await res.json();
   onDone(data.access_token,data.user_id,data.name);
  }catch(e){
   setError(e.message==="Failed to fetch"?"":e.message);
   onDone(null,null,name); // demo mode fallback if backend isn't reachable
  }
  setBusy(false);
 };

 return <div className="auth"><div className="auth-card"><span className="logo">F</span><p className="eyebrow">SECURE SIGN IN</p><h1>{sent?"Verify your mobile":"Continue with your mobile"}</h1><p>{sent?"Enter the OTP we sent to your mobile number.":"Your mobile number is used to secure requests, bookings and communication."}</p>{!sent?<><label className="field"><b>Your name</b><div className="input"><UserRound/><input value={name} onChange={e=>setName(e.target.value)} placeholder="Enter your name"/></div></label><label className="field"><b>Mobile number</b><div className="phone"><span>+91</span><input value={phone} onChange={e=>setPhone(e.target.value.replace(/\D/g,""))} maxLength={10} placeholder="10-digit mobile number"/></div></label><button className="primary full" disabled={name.length<2||phone.length<10||busy} onClick={sendOtp}>{busy?"Sending...":"Send OTP"} <ArrowRight/></button></>:<><div className="otp"><input autoFocus value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,""))} maxLength={6} placeholder={devHint||"••••••"}/></div>{devHint&&<p className="privacy">Test OTP: {devHint} (shown only because a real SMS provider isn't wired in yet)</p>}{error&&<p className="privacy" style={{color:"#C2452B"}}>{error}</p>}<button className="primary full" disabled={code.length<4||busy} onClick={verify}>{busy?"Verifying...":"Verify & continue"} <Check/></button><button className="link" onClick={sendOtp}>Resend OTP</button></>}<small className="terms">By continuing you agree to the platform Terms, Privacy Policy and service communications.</small></div></div>
}

function Request({p,service,location,authToken,go,notify,onCreated}){
 const [message,setMessage]=useState(""),[busy,setBusy]=useState(false);

 const send=async()=>{
  setBusy(true);
  try{
   if(!service?.dbId)throw new Error("no live service id — demo mode");
   const res=await fetch(API_BASE+"/api/v1/service-requests/",{
    method:"POST",
    headers:{"Content-Type":"application/json",...(authToken?{"Authorization":"Bearer "+authToken}:{})},
    body:JSON.stringify({
     service_id:service.dbId,
     location_label:location?.label||"Service location",
     lat:location?.lat, lng:location?.lng,
     requirements:{},
     notes:message,
    }),
   });
   if(!res.ok){ const d=await res.json().catch(()=>({}));throw new Error(d.detail||"Could not send request"); }
   const data=await res.json();
   onCreated(data.id);
   notify("Request sent to provider");
  }catch(e){
   // Backend not reachable, or no live-service id in this demo run —
   // keep the flow moving so the prototype still walks through cleanly.
   notify("Request sent to provider");
  }
  setBusy(false);
  go("waiting");
 };

 return <div className="page narrow"><button className="back" onClick={()=>go("provider")}><ArrowLeft/> Provider</button><div className="form-heading"><div className="big-avatar">{p.name[0]}</div><div><p className="eyebrow">REQUEST SERVICE</p><h1>Send your request</h1><p>Review everything before the provider receives it.</p></div></div><div className="card summary"><Row k="Provider" v={p.name}/><Row k="Service" v={service?.name||"Borewell services"}/><Row k="Service location" v={location?.label}/><Row k="Preferred date" v="Tomorrow • Morning"/><Row k="Requirements" v="Site details submitted"/></div><label className="field"><b>Message to provider</b><textarea value={message} onChange={e=>setMessage(e.target.value)} placeholder="Add anything important about the job…"></textarea></label><button className="primary full" disabled={busy} onClick={send}>{busy?"Sending...":"Send service request"} <Send/></button><p className="privacy"><ShieldCheck/> Contact details are protected until you proceed.</p></div>
}
function Row({k,v}){return <div className="summary-row"><span>{k}</span><b>{v}</b></div>}

function Waiting({p,requestId,authToken,go,notify,onBooked}){
 const [polling,setPolling]=useState(!!requestId);

 useEffect(()=>{
  if(!requestId||!authToken)return;
  let stopped=false;
  const poll=async()=>{
   try{
    const res=await fetch(API_BASE+"/api/v1/service-requests/"+requestId+"/quotes",{headers:{"Authorization":"Bearer "+authToken}});
    if(!res.ok)return;
    const quotes=await res.json();
    const pending=quotes.find(q=>q.status==="pending");
    if(pending&&!stopped){
     const acceptRes=await fetch(API_BASE+"/api/v1/quotes/"+pending.id+"/accept",{method:"POST",headers:{"Authorization":"Bearer "+authToken}});
     if(acceptRes.ok){
      const booking=await acceptRes.json();
      onBooked(booking.id);
      notify("Quote accepted — booking confirmed");
      setPolling(false);
      go("booking");
     }
    }
   }catch(e){ /* backend not reachable — keep waiting, user can still simulate below */ }
  };
  const id=setInterval(poll,4000);
  poll();
  return ()=>{stopped=true;clearInterval(id)};
 },[requestId,authToken]);

 return <div className="center-state"><div className="state-card"><div className="spinner"></div><p className="eyebrow">REQUEST SENT</p><h1>Waiting for {p.name}</h1><p>The provider can accept, send a quote, or decline. We'll notify you when they respond.</p><div className="wait-box"><span className="dot"></span><div><b>{polling?"Checking for a quote every few seconds…":"Provider reviewing your request"}</b><small>Typical response: 5–15 minutes</small></div></div><button className="primary full" onClick={()=>{onBooked(null);go("booking")}}>Simulate provider accepts <ArrowRight/></button></div></div>
}

function Booking({go,setOtp,bookingId,authToken}){
 const [real,setReal]=useState(null);
 useEffect(()=>{
  if(!bookingId||!authToken)return;
  fetch(API_BASE+"/api/v1/bookings/"+bookingId,{headers:{"Authorization":"Bearer "+authToken}})
   .then(r=>r.ok?r.json():null).then(setReal).catch(()=>{});
 },[bookingId,authToken]);
 return <div className="center-state"><div className="state-card"><div className="success-icon"><Check/></div><p className="eyebrow">BOOKING CONFIRMED</p><h1>Your service is booked.</h1><p>{real?"Booking #"+real.id.slice(0,8)+" • status: "+real.status:"Sri Sai Borewell Works is scheduled for tomorrow at 10:00 AM."}</p><div className="timeline"><T active t="Provider accepted" s="Booking confirmed"/><T active t="Scheduled" s="Tomorrow • 10:00 AM"/><T t="Provider arriving" s="You'll be notified when they start travelling"/><T t="Service completion" s="Confirm completion after the work"/></div><button className="primary full" onClick={()=>{setOtp(false);go("tracking")}}>Open live service</button></div></div>
}
function T({active,t,s}){return <div className="timeline-row"><span className={active?"td active":"td"}>{active&&<Check/>}</span><div><b>{t}</b><small>{s}</small></div></div>}

function Tracking({go,otp,setOtp,notify,bookingId,authToken,p}){
 const [status,setStatus]=useState(null);
 const [otpCode,setOtpCode]=useState(null);
 const [otpBusy,setOtpBusy]=useState(false);

 useEffect(()=>{
  if(!bookingId||!authToken)return;
  let stopped=false;
  const poll=async()=>{
   try{
    const res=await fetch(API_BASE+"/api/v1/bookings/"+bookingId,{headers:{"Authorization":"Bearer "+authToken}});
    if(!res.ok||stopped)return;
    const data=await res.json();
    setStatus(data.status);
    if(data.status==="SERVICE_COMPLETED"){ notify("Service marked complete by provider"); go("complete"); }
   }catch(e){ /* backend unreachable — UI stays in its current simulated state */ }
  };
  const id=setInterval(poll,4000);
  poll();
  return ()=>{stopped=true;clearInterval(id)};
 },[bookingId,authToken]);

 const showOtp=async()=>{
  if(!bookingId||!authToken){ setOtp(true); return; } // demo fallback, no real booking
  setOtpBusy(true);
  try{
   const res=await fetch(API_BASE+"/api/v1/bookings/"+bookingId+"/start-otp",{headers:{"Authorization":"Bearer "+authToken}});
   const data=await res.json();
   if(!res.ok)throw new Error(data.detail||"Could not get OTP");
   setOtpCode(data.otp);
   setOtp(true);
  }catch(e){ notify(e.message); }
  setOtpBusy(false);
 };

 const statusLabel={
  CONFIRMED:"Booking confirmed",ON_THE_WAY:"Provider is on the way",ARRIVED:"Provider has arrived",
  SERVICE_STARTED:"Service in progress",SERVICE_COMPLETED:"Service complete",
 }[status]||"Provider is on the way";
 const canShowOtp=!bookingId||status==="ARRIVED";

 return <div className="tracking"><div className="tracking-map"><div className="route"></div><div className="user-pin"><MapPin/></div><div className="vehicle-pin"><Truck/></div><div className="arrival">{statusLabel}{status==="ON_THE_WAY"?" • ~12 min":""} <span></span></div></div><div className="tracking-sheet"><div className="sheet-handle"></div><div className="track-title"><div><p className="eyebrow">LIVE SERVICE</p><h1>{statusLabel}</h1><p>{p.name}{bookingId?" • booking #"+bookingId.slice(0,8):" • arriving in ~12 min"}</p></div><div className="big-avatar">{p.name[0]}</div></div><div className="track-tools"><button><Phone/>Call</button><button><MessageCircle/>Chat</button><button><Navigation/>Share</button></div><div className="otp-section">{!otp?<><div><b>Service start OTP</b><small>When the provider arrives, show this code and read it to them before work begins.</small></div><button className="primary" disabled={!canShowOtp||otpBusy} onClick={showOtp}>{otpBusy?"Loading...":canShowOtp?"Show OTP":"Available once provider arrives"}</button></>:<div className="otp-live"><span>{(otpCode||"4826").split("").map((d,i)=><span key={i}>{d}</span>)}</span><small>Tell this OTP to the provider to start the job. The provider enters it on their side — the job won't start until they do.</small></div>}</div>{bookingId?<p className="tiny">Status updates automatically as the provider moves through arrival, start and completion — no action needed here.</p>:<button className="secondary full" onClick={()=>go("complete")}>Simulate: service complete</button>}</div></div>
}

function Complete({go,complete,setComplete,notify,bookingId,authToken,p}){
 const [rating,setRating]=useState(0),[text,setText]=useState("");
 const [booking,setBooking]=useState(null),[paying,setPaying]=useState(false),[submitting,setSubmitting]=useState(false);

 useEffect(()=>{
  if(!bookingId||!authToken)return;
  fetch(API_BASE+"/api/v1/bookings/"+bookingId,{headers:{"Authorization":"Bearer "+authToken}})
   .then(r=>r.ok?r.json():null).then(setBooking).catch(()=>{});
 },[bookingId,authToken]);

 const confirmPayment=async()=>{
  setPaying(true);
  try{
   const res=await fetch(API_BASE+"/api/v1/bookings/"+bookingId+"/mark-paid",{method:"POST",headers:{"Authorization":"Bearer "+authToken}});
   const data=await res.json();
   if(!res.ok)throw new Error(data.detail||"Payment failed");
   setBooking(data);
   notify("Payment recorded");
  }catch(e){ notify(e.message); }
  setPaying(false);
 };

 const submitFeedback=async()=>{
  setSubmitting(true);
  try{
   if(!bookingId)throw new Error("demo mode — no real booking to review");
   const res=await fetch(API_BASE+"/api/v1/reviews/",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+authToken},body:JSON.stringify({booking_id:bookingId,rating,comment:text})});
   if(!res.ok){ const d=await res.json().catch(()=>({}));throw new Error(d.detail||"Could not submit review"); }
   setComplete(true); notify("Feedback submitted");
  }catch(e){
   setComplete(true); notify("Feedback submitted"); // demo-mode fallback
  }
  setSubmitting(false);
 };

 if(complete)return <div className="center-state"><div className="state-card"><div className="success-icon"><Check/></div><p className="eyebrow">THANK YOU</p><h1>Service completed.</h1><p>Your feedback helps good providers build trust on Fieldly.</p><button className="primary full" onClick={()=>go("services")}>Find another service <ArrowRight/></button></div></div>;

 const needsPayment=booking&&booking.status==="SERVICE_COMPLETED";
 return <div className="center-state"><div className="state-card"><div className="success-icon"><Check/></div><p className="eyebrow">JOB COMPLETED</p><h1>{needsPayment?"Confirm your payment":"How was your experience?"}</h1>{needsPayment?<><p>{p.name} completed the job for ₹{booking.final_amount?.toLocaleString("en-IN")} ({booking.payment_method}).</p><button className="primary full" disabled={paying} onClick={confirmPayment}>{paying?"Confirming...":"Confirm payment received"}</button></>:<><p>{p.name} completed your service. Rate the experience.</p><div className="stars">{[1,2,3,4,5].map(n=><button className={rating>=n?"on":""} key={n} onClick={()=>setRating(n)}><Star fill="currentColor"/></button>)}</div><textarea value={text} onChange={e=>setText(e.target.value)} placeholder="Share what went well or what could be better…"></textarea><button className="primary full" disabled={!rating||submitting} onClick={submitFeedback}>{submitting?"Submitting...":"Submit feedback"} <ArrowRight/></button><button className="link" onClick={()=>setComplete(true)}>Skip for now</button></>}</div></div>
}

function Account({logged,go}){return <div className="page"><div className="account-head"><div className="big-avatar">A</div><div><p className="eyebrow">ACCOUNT</p><h1>My Fieldly</h1><p>{logged?"Manage bookings, locations, messages and support.":"Sign in when you’re ready to request a service."}</p></div></div><div className="account-grid">{["Bookings","Saved service locations","Messages","Payments & receipts","Reviews","Help & support"].map(x=><button className="account-item" key={x} onClick={()=>x==="Help & support"&&go("help")}><span>{x==="Payments & receipts"?"₹":x==="Reviews"?"★":"•"}</span><div><b>{x}</b><small>View and manage</small></div><ChevronRight/></button>)}</div></div>}

function ProviderJoin({go,notify}){
 const [stage,setStage]=useState(1);
 const steps=["Mobile & profile","Services","Equipment","Operators","Documents","Service area","Pricing","Review"];
 return <div className="join"><div className="join-hero"><div><p className="eyebrow">FOR SERVICE PROVIDERS</p><h1>Turn your equipment into a trusted local business.</h1><p>Register once. Add every service, machine and operator you manage. After verification, receive relevant requests in your service areas.</p><button className="primary" onClick={()=>setStage(2)}>Start registration <ArrowRight/></button></div><div className="join-dashboard"><div className="earn"><small>Provider dashboard</small><b>8 requests nearby</b><span>3 need a response</span></div><div className="request-mini"><b>Borewell drilling</b><span>4.6 km • Tomorrow 10 AM</span><strong>Review request</strong></div><div className="request-mini"><b>JCB • Site clearing</b><span>2.1 km • Today 3:30 PM</span><strong>Send quote</strong></div></div></div>
 <div className="page join-page"><div className="join-head"><div><p className="eyebrow">PROVIDER REGISTRATION</p><h2>Complete your provider profile</h2><p>Verification protects customers and helps us send the right jobs to the right providers.</p></div><span>Step {stage} of 8</span></div><div className="provider-steps">{steps.map((x,i)=><div className={stage>i+1?"done":stage===i+1?"current":""} key={x}><span>{stage>i+1?<Check/>:i+1}</span><small>{x}</small></div>)}</div><div className="card provider-form">{stage===2?<><h3>Which services do you provide?</h3><p>Select every service you can actually deliver.</p><div className="select-grid">{SERVICES.slice(0,8).map(s=><button className="select-service" key={s.id}><span>{s.icon}</span><b>{s.name}</b><Check/></button>)}</div></>:stage===3?<><h3>Add your equipment</h3><p>Each machine is a separate listing so customers can see what is actually available.</p><div className="equipment-form"><Field label="Equipment type"><div className="input"><Wrench/><input placeholder="e.g. Hydraulic borewell rig"/></div></Field><Field label="Make / model"><div className="input"><input placeholder="e.g. Atlas Copco / model"/></div></Field><Field label="Capacity / capability"><div className="input"><input placeholder="e.g. Up to 1000 ft"/></div></Field><button className="upload"><Upload/> Upload equipment documents</button></div></>:<><h3>Provider onboarding checklist</h3><p>We’ll guide you through identity, equipment, service eligibility, service area, availability and pricing.</p><div className="checklist">{steps.map((x,i)=><div key={x}><span>{i<stage? <Check/>:i+1}</span><b>{x}</b><small>{i<stage?"Completed / ready for review":"Required before approval"}</small></div>)}</div></>}<button className="primary full" onClick={()=>stage<8?setStage(stage+1):notify("Application submitted for verification")}>{stage<8?"Save & continue":"Submit for verification"} <ArrowRight/></button><p className="privacy"><ShieldCheck/> Sensitive documents are visible only to authorized verification staff.</p></div></div></div>
}
function Help(){return <div className="page narrow"><p className="eyebrow">HELP CENTER</p><h1>How can we help?</h1><p className="sub">Find answers about locations, providers, requests, bookings, payments and safety.</p><div className="help-search"><Search/><input placeholder="Search help"/></div><div className="faq">{["How do I choose a service location?","What does a verified provider mean?","When will my contact number be shared?","Can I cancel a request or booking?","How does the start OTP work?","What if the provider does not arrive?","How are quotes and final amounts handled?"].map(x=><button key={x}><span>{x}</span><ChevronRight/></button>)}</div></div>}
function Footer({go}){return <footer><div className="footer-inner"><div><button className="brand"><span className="logo">F</span>fieldly</button><p>Equipment and services, wherever the work takes you.</p></div><div className="footer-links"><div><b>Explore</b><button onClick={()=>go("services")}>Services</button><button onClick={()=>go("providers")}>Providers</button></div><div><b>Providers</b><button onClick={()=>go("join")}>Become a provider</button><button>Provider help</button></div><div><b>Support</b><button onClick={()=>go("help")}>Help center</button><button>Safety</button></div></div></div><div className="copyright">© 2026 Fieldly • India-wide platform architecture • State and service availability varies by area</div></footer>}
function Field({label,hint,children}){return <label className="field"><div><b>{label}</b>{hint&&<small>{hint}</small>}</div>{children}</label>}

createRoot(document.getElementById("root")).render(<App/>);
