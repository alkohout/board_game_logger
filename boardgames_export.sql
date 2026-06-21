--
-- PostgreSQL database dump
--

\restrict sfOLOIStoCNhxvapnz9LBbgEiI04a2OirMN6tx7bJyusJxibKfaPQgfjlgfHA7i

-- Dumped from database version 16.4
-- Dumped by pg_dump version 17.8 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: games; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.games (
    id integer NOT NULL,
    date_played date NOT NULL,
    game_title character varying(255) NOT NULL,
    notes text,
    result character varying(50),
    my_score character varying(50),
    bot_score character varying(50),
    level character varying(50)
);


ALTER TABLE public.games OWNER TO postgres;

--
-- Name: games_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.games_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.games_id_seq OWNER TO postgres;

--
-- Name: games_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.games_id_seq OWNED BY public.games.id;


--
-- Name: imperium; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.imperium AS
 SELECT id,
    date_played,
    game_title,
    notes,
    result,
    my_score,
    bot_score,
    level
   FROM public.games
  WHERE ((game_title)::text ~~* '%Imperium%'::text);


ALTER VIEW public.imperium OWNER TO postgres;

--
-- Name: sleeping_gods; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sleeping_gods (
    location integer,
    part character varying(50),
    required_keyword character varying(50),
    gained_keyword character varying(50),
    visited boolean,
    notes character varying(500),
    combat boolean DEFAULT false,
    combat_level integer DEFAULT 0,
    gained character varying(100) DEFAULT ''::character varying,
    lost character varying(100) DEFAULT ''::character varying,
    req_coins integer DEFAULT 0,
    req_meat integer DEFAULT 0,
    req_veg integer DEFAULT 0,
    req_grain integer DEFAULT 0,
    req_artifacts integer DEFAULT 0,
    gain_coins integer DEFAULT 0,
    gain_meat integer DEFAULT 0,
    gain_veg integer DEFAULT 0,
    gain_grain integer DEFAULT 0,
    gain_artifacts integer DEFAULT 0,
    req_wood integer DEFAULT 0,
    gain_wood integer DEFAULT 0,
    gain_xp integer DEFAULT 0,
    gain_ship_damage integer DEFAULT 0,
    gain_ship_repair integer DEFAULT 0,
    gain_crew_damage integer DEFAULT 0,
    gain_crew_health integer DEFAULT 0,
    gain_low_morale integer DEFAULT 0,
    gain_fright integer DEFAULT 0,
    gain_venom integer DEFAULT 0,
    gain_weakness integer DEFAULT 0,
    gain_madness integer DEFAULT 0,
    remove_low_morale integer DEFAULT 0,
    remove_fright integer DEFAULT 0,
    remove_venom integer DEFAULT 0,
    remove_weakness integer DEFAULT 0,
    remove_madness integer DEFAULT 0,
    totem character varying(80) DEFAULT 0,
    challenge character varying(20) DEFAULT 0,
    challenge_level integer DEFAULT 0,
    gain_totem character varying(80) DEFAULT 0,
    gain_adventure integer DEFAULT 0,
    defeats integer DEFAULT 0,
    id integer NOT NULL
);


ALTER TABLE public.sleeping_gods OWNER TO postgres;

--
-- Name: sleeping_gods_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sleeping_gods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sleeping_gods_id_seq OWNER TO postgres;

--
-- Name: sleeping_gods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sleeping_gods_id_seq OWNED BY public.sleeping_gods.id;


--
-- Name: sleeping_gods_totems; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sleeping_gods_totems (
    id integer NOT NULL,
    totem character varying(100) NOT NULL,
    found boolean
);


ALTER TABLE public.sleeping_gods_totems OWNER TO postgres;

--
-- Name: sleeping_gods_totems_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sleeping_gods_totems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sleeping_gods_totems_id_seq OWNER TO postgres;

--
-- Name: sleeping_gods_totems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sleeping_gods_totems_id_seq OWNED BY public.sleeping_gods_totems.id;


--
-- Name: games id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.games ALTER COLUMN id SET DEFAULT nextval('public.games_id_seq'::regclass);


--
-- Name: sleeping_gods id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sleeping_gods ALTER COLUMN id SET DEFAULT nextval('public.sleeping_gods_id_seq'::regclass);


--
-- Name: sleeping_gods_totems id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sleeping_gods_totems ALTER COLUMN id SET DEFAULT nextval('public.sleeping_gods_totems_id_seq'::regclass);


--
-- Data for Name: games; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.games (id, date_played, game_title, notes, result, my_score, bot_score, level) FROM stdin;
1959	2023-01-01	7 Wonders	\N	\N	\N	\N	\N
1960	2024-10-28	7 Wonders	\N	\N	\N	\N	\N
1961	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1962	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1963	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1964	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1965	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1966	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1967	2023-01-01	7 Wonders: Architects	\N	\N	\N	\N	\N
1968	2023-01-01	Aquamarine	\N	\N	\N	\N	\N
1969	2023-01-01	Aquamarine	\N	\N	\N	\N	\N
1970	2024-10-12	Ares Expedition 	\N	\N	\N	\N	\N
1971	2024-10-26	Ares Expedition 	\N	\N	\N	\N	\N
1972	2024-10-26	Ares Expedition 	\N	\N	\N	\N	\N
2013	2023-01-01	Ark nova minima	\N	\N	\N	\N	\N
2014	2023-01-01	Ark nova minima	\N	\N	\N	\N	\N
2015	2023-01-01	Ark nova minima	\N	\N	\N	\N	\N
2016	2024-02-04	Ark nova minima	\N	\N	\N	\N	\N
2017	2024-02-06	Ark nova minima	\N	\N	\N	\N	\N
2018	2024-02-10	Ark nova minima	\N	\N	\N	\N	\N
2019	2023-01-01	Azul	\N	\N	\N	\N	\N
2020	2023-01-01	Azul	\N	\N	\N	\N	\N
2021	2023-01-01	Azul	\N	\N	\N	\N	\N
2022	2023-01-01	Azul	\N	\N	\N	\N	\N
2023	2024-02-09	Azul	\N	\N	\N	\N	\N
2024	2024-05-14	Azul	\N	\N	\N	\N	\N
2025	2024-05-30	Azul	\N	\N	\N	\N	\N
2026	2024-07-14	Azul	\N	\N	\N	\N	\N
2027	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2028	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2029	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2030	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2031	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2032	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2033	2023-01-01	Bah Humbug	\N	\N	\N	\N	\N
2034	2023-01-01	Bananagrams	\N	\N	\N	\N	\N
2035	2023-01-01	Bananagrams	\N	\N	\N	\N	\N
2036	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2037	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2038	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2039	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2040	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2041	2023-01-01	The Bears and the Bees	\N	\N	\N	\N	\N
2042	2024-05-28	The Bears and the Bees	\N	\N	\N	\N	\N
2043	2024-05-30	The Bears and the Bees	\N	\N	\N	\N	\N
2044	2024-06-01	The Bears and the Bees	\N	\N	\N	\N	\N
2045	2024-06-14	The Bears and the Bees	\N	\N	\N	\N	\N
2046	2024-06-15	The Bears and the Bees	\N	\N	\N	\N	\N
2047	2024-06-15	The Bears and the Bees	\N	\N	\N	\N	\N
2048	2024-06-21	The Bears and the Bees	\N	\N	\N	\N	\N
2049	2024-06-25	The Bears and the Bees	\N	\N	\N	\N	\N
2050	2024-06-30	The Bears and the Bees	\N	\N	\N	\N	\N
2051	2024-07-04	The Bears and the Bees	\N	\N	\N	\N	\N
2052	2024-07-10	The Bears and the Bees	\N	\N	\N	\N	\N
2053	2024-08-02	The Bears and the Bees	\N	\N	\N	\N	\N
2054	2024-08-03	The Bears and the Bees	\N	\N	\N	\N	\N
2055	2023-01-01	Beez	\N	\N	\N	\N	\N
2056	2023-01-01	Beez	\N	\N	\N	\N	\N
2057	2023-01-01	Beez	\N	\N	\N	\N	\N
2058	2023-01-01	Brass: Birgingham	\N	\N	\N	\N	\N
2059	2023-01-01	Brass: Birgingham	\N	\N	\N	\N	\N
2060	2023-01-01	Brass: Lancashire	\N	\N	\N	\N	\N
2061	2023-01-01	Brass: Lancashire	\N	\N	\N	\N	\N
2062	2023-01-01	Brass: Lancashire	\N	\N	\N	\N	\N
2063	2023-01-01	Brass: Lancashire	\N	\N	\N	\N	\N
2064	2024-09-01	Bohnanza	\N	\N	\N	\N	\N
2065	2024-09-13	Bohnanza	\N	\N	\N	\N	\N
2066	2024-09-17	Bohnanza	\N	\N	\N	\N	\N
2067	2024-09-28	Bohnanza	\N	\N	\N	\N	\N
2068	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2069	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2070	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2071	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2072	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2073	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2074	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2075	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2076	2023-01-01	Bohnanza: My First	\N	\N	\N	\N	\N
2077	2024-04-03	Bohnanza: My First	\N	\N	\N	\N	\N
2078	2024-05-01	Bohnanza: My First	\N	\N	\N	\N	\N
2079	2023-01-01	Bohnanza: Wūrfel	\N	\N	\N	\N	\N
2080	2023-01-01	Bohnanza: Wūrfel	\N	\N	\N	\N	\N
2081	2023-01-01	Bohnanza: Wūrfel	\N	\N	\N	\N	\N
2082	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2083	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2084	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2085	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2086	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2087	2023-01-01	Busy Beaks	\N	\N	\N	\N	\N
2088	2024-04-05	Busy Beaks	\N	\N	\N	\N	\N
2089	2023-01-01	Calico	\N	\N	\N	\N	\N
2090	2024-01-18	Calico	\N	\N	\N	\N	\N
2091	2024-02-10	Calico	\N	\N	\N	\N	\N
2092	2024-02-23	Calico	\N	\N	\N	\N	\N
2093	2024-02-28	Calico	\N	\N	\N	\N	\N
2094	2024-03-11	Calico	\N	\N	\N	\N	\N
2095	2024-03-18	Calico	\N	\N	\N	\N	\N
2096	2024-08-03	Calico	\N	\N	\N	\N	\N
2097	2023-01-01	Canvas	\N	\N	\N	\N	\N
2098	2023-01-01	Canvas	\N	\N	\N	\N	\N
2099	2023-01-01	Canvas	\N	\N	\N	\N	\N
2100	2023-01-01	Canvas	\N	\N	\N	\N	\N
2101	2023-01-01	Canvas	\N	\N	\N	\N	\N
2102	2023-01-01	Canvas	\N	\N	\N	\N	\N
2103	2023-01-01	Canvas	\N	\N	\N	\N	\N
2104	2023-01-01	Canvas	\N	\N	\N	\N	\N
2105	2024-01-25	Canvas	\N	\N	\N	\N	\N
2106	2024-03-05	Canvas	\N	\N	\N	\N	\N
2107	2023-01-01	Carcassonne: The City	\N	\N	\N	\N	\N
2108	2023-01-01	Carcassonne: The City	\N	\N	\N	\N	\N
2109	2023-01-01	Carcassonne: The City	\N	\N	\N	\N	\N
2110	2023-01-01	Carcassonne: The City	\N	\N	\N	\N	\N
2111	2024-02-11	Carcassonne: The City	\N	\N	\N	\N	\N
2112	2023-01-01	Carcassonne: Wheel of Fortune	\N	\N	\N	\N	\N
2113	2023-01-01	Carcassonne: Wheel of Fortune	\N	\N	\N	\N	\N
2114	2023-01-01	Cards: Canasta	\N	\N	\N	\N	\N
2115	2023-01-01	Cards: Canasta	\N	\N	\N	\N	\N
2116	2023-01-01	Cards: Canasta	\N	\N	\N	\N	\N
2117	2024-04-26	Cards: Canasta	\N	\N	\N	\N	\N
2118	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2119	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2120	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2121	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2122	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2123	2023-01-01	Cards: James Bond	\N	\N	\N	\N	\N
2124	2024-01-20	Cards: Poker	\N	\N	\N	\N	\N
2125	2024-02-03	Cards: Poker	\N	\N	\N	\N	\N
2126	2023-01-01	Cards: rummy	\N	\N	\N	\N	\N
2127	2023-01-01	Cards: rummy	\N	\N	\N	\N	\N
2128	2023-01-01	Cards: rummy	\N	\N	\N	\N	\N
2129	2024-02-03	Cards: Wizard	\N	\N	\N	\N	\N
2130	2024-02-06	Cards: Wizard	\N	\N	\N	\N	\N
2131	2024-02-07	Cards: Wizard	\N	\N	\N	\N	\N
2132	2024-02-08	Cards: Wizard	\N	\N	\N	\N	\N
2133	2024-02-11	Cards: Wizard	\N	\N	\N	\N	\N
2134	2024-02-11	Cards: Wizard	\N	\N	\N	\N	\N
2135	2024-10-07	Cascadia	\N	\N	\N	\N	\N
2136	2024-10-07	Cascadia	\N	\N	\N	\N	\N
2137	2024-10-08	Cascadia	\N	\N	\N	\N	\N
2138	2024-10-09	Cascadia	\N	\N	\N	\N	\N
2139	2024-10-10	Cascadia	\N	\N	\N	\N	\N
2140	2024-10-12	Cascadia	\N	\N	\N	\N	\N
2141	2024-10-21	Cascadia	\N	\N	\N	\N	\N
2142	2024-10-25	Cascadia	\N	\N	\N	\N	\N
2143	2024-10-26	Cascadia	\N	\N	\N	\N	\N
2144	2024-10-06	Castle Panic	\N	\N	\N	\N	\N
2145	2024-10-09	Castle Panic	\N	\N	\N	\N	\N
2146	2024-10-09	Castle Panic	\N	\N	\N	\N	\N
2147	2023-01-01	Catan	\N	\N	\N	\N	\N
2148	2023-01-01	Catan	\N	\N	\N	\N	\N
2149	2023-01-01	Catan	\N	\N	\N	\N	\N
2150	2023-01-01	Catan: Junior	\N	\N	\N	\N	\N
2151	2023-01-01	Catan: Junior	\N	\N	\N	\N	\N
2152	2023-01-01	Catan: Junior	\N	\N	\N	\N	\N
2153	2024-01-24	Century: Eastern	\N	\N	\N	\N	\N
2154	2024-03-07	Century: Eastern	\N	\N	\N	\N	\N
2155	2024-03-07	Century: Eastern	\N	\N	\N	\N	\N
2156	2024-03-08	Century: Eastern	\N	\N	\N	\N	\N
2157	2023-01-01	Century: A New World	\N	\N	\N	\N	\N
2158	2023-01-01	Century: A New World	\N	\N	\N	\N	\N
2159	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2160	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2161	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2162	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2163	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2164	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2165	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2166	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2167	2023-01-01	Century: Spice Road	\N	\N	\N	\N	\N
2168	2024-04-01	Century: Spice Road	\N	\N	\N	\N	\N
2169	2024-04-03	Century: Spice Road	\N	\N	\N	\N	\N
2170	2024-05-14	Century: Spice Road	\N	\N	\N	\N	\N
2171	2023-01-01	Cluedo	\N	\N	\N	\N	\N
2172	2023-01-01	Cluedo	\N	\N	\N	\N	\N
2173	2023-01-01	Cluedo	\N	\N	\N	\N	\N
2174	2023-01-01	Cluedo	\N	\N	\N	\N	\N
2175	2023-01-01	Cluedo	\N	\N	\N	\N	\N
2176	2024-08-16	Cluedo	\N	\N	\N	\N	\N
2177	2023-01-01	Cluedo: junior	\N	\N	\N	\N	\N
2178	2023-01-01	Cluedo: junior	\N	\N	\N	\N	\N
2179	2024-01-25	Cluedo: junior	\N	\N	\N	\N	\N
2180	2024-08-23	Cluedo: junior	\N	\N	\N	\N	\N
2181	2024-08-24	Cluedo: junior	\N	\N	\N	\N	\N
2182	2023-01-01	Coconuts	\N	\N	\N	\N	\N
2183	2023-01-01	Concordia	\N	\N	\N	\N	\N
2184	2023-01-01	Concordia	\N	\N	\N	\N	\N
2185	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2186	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2187	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2188	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2189	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2190	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2191	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2192	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2193	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2194	2023-01-01	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2195	2024-09-29	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2196	2024-10-04	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2197	2024-10-04	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2198	2024-10-06	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2199	2024-10-07	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2200	2024-10-07	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2201	2024-10-08	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2202	2024-10-09	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2203	2024-10-12	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2204	2024-10-26	The Crew: Mission Deep Sea	\N	\N	\N	\N	\N
2205	2023-01-01	Dino World	\N	\N	\N	\N	\N
2206	2023-01-01	Dino World	\N	\N	\N	\N	\N
2207	2023-01-01	Dino World	\N	\N	\N	\N	\N
2208	2023-01-01	Dino World	\N	\N	\N	\N	\N
2209	2023-01-01	Dino World	\N	\N	\N	\N	\N
2210	2023-01-01	Dino World	\N	\N	\N	\N	\N
2211	2023-01-01	Dino World	\N	\N	\N	\N	\N
2212	2023-01-01	Dino World	\N	\N	\N	\N	\N
2213	2023-01-01	Dino World	\N	\N	\N	\N	\N
2214	2023-01-01	Dino World	\N	\N	\N	\N	\N
2215	2023-01-01	Dino World	\N	\N	\N	\N	\N
2216	2023-01-01	Dino World	\N	\N	\N	\N	\N
2217	2023-01-01	Dino World	\N	\N	\N	\N	\N
2218	2023-01-01	Dino World	\N	\N	\N	\N	\N
2219	2023-01-01	Dino World	\N	\N	\N	\N	\N
2220	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2221	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2222	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2223	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2224	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2225	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2226	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2227	2023-01-01	Dinosaur Tea Party	\N	\N	\N	\N	\N
2228	2024-10-16	Dinosaur Tea Party	\N	\N	\N	\N	\N
2229	2023-01-01	Dominion	\N	\N	\N	\N	\N
2230	2023-01-01	Dominion	\N	\N	\N	\N	\N
2231	2024-02-16	Dominion	\N	\N	\N	\N	\N
2232	2024-03-24	Dominion	\N	\N	\N	\N	\N
2233	2023-01-01	Draftosaurus	\N	\N	\N	\N	\N
2234	2023-01-01	Draftosaurus	\N	\N	\N	\N	\N
2235	2023-01-01	Draftosaurus	\N	\N	\N	\N	\N
2236	2023-01-01	Draftosaurus	\N	\N	\N	\N	\N
2237	2023-01-01	Draftosaurus	\N	\N	\N	\N	\N
2238	2024-02-03	Draftosaurus	\N	\N	\N	\N	\N
2239	2024-09-13	Draftosaurus	\N	\N	\N	\N	\N
2240	2023-01-01	Dragomino	\N	\N	\N	\N	\N
2241	2023-01-01	Dragomino	\N	\N	\N	\N	\N
2242	2023-01-01	Dragomino	\N	\N	\N	\N	\N
2243	2023-01-01	Dragomino	\N	\N	\N	\N	\N
2244	2023-01-01	Dragomino	\N	\N	\N	\N	\N
2245	2024-06-28	Dragomino	\N	\N	\N	\N	\N
2246	2023-01-01	Dragon Parks	\N	\N	\N	\N	\N
2247	2023-01-01	Dragon Parks	\N	\N	\N	\N	\N
2248	2023-01-01	Dragon Parks	\N	\N	\N	\N	\N
2249	2023-01-01	Dragon Parks	\N	\N	\N	\N	\N
2250	2024-01-22	Dragon Parks	\N	\N	\N	\N	\N
2251	2024-04-05	Dragon Parks	\N	\N	\N	\N	\N
2252	2024-09-13	Dragon Parks	\N	\N	\N	\N	\N
2253	2023-01-01	Dragonstark	\N	\N	\N	\N	\N
2254	2023-01-01	Dragonstark	\N	\N	\N	\N	\N
2255	2023-01-01	Dragonstark	\N	\N	\N	\N	\N
2256	2023-01-01	Dragonstark	\N	\N	\N	\N	\N
2257	2023-01-01	Dragonstark	\N	\N	\N	\N	\N
2258	2024-05-30	Dragonstark	\N	\N	\N	\N	\N
2259	2024-06-17	Dragonstark	\N	\N	\N	\N	\N
2260	2023-01-01	Everdell: My Lil'	\N	\N	\N	\N	\N
2261	2023-01-01	Everdell: My Lil'	\N	\N	\N	\N	\N
2262	2023-01-01	Everdell: My Lil'	\N	\N	\N	\N	\N
2263	2023-01-01	Everdell: My Lil'	\N	\N	\N	\N	\N
2264	2023-01-01	Everdell: My Lil'	\N	\N	\N	\N	\N
2265	2024-03-15	Everdell: My Lil'	\N	\N	\N	\N	\N
2266	2024-10-26	Exit 	\N	\N	\N	\N	\N
2267	2023-01-01	Exploding Kittens	\N	\N	\N	\N	\N
2268	2023-01-01	Exploding Kittens	\N	\N	\N	\N	\N
2269	2023-01-01	Fairytale in my pocket	\N	\N	\N	\N	\N
2270	2023-01-01	Fairytale in my pocket	\N	\N	\N	\N	\N
2271	2023-01-01	Fairytale in my pocket	\N	\N	\N	\N	\N
2272	2024-03-23	Fairytale in my pocket	\N	\N	\N	\N	\N
2273	2024-08-26	Fairytale in my pocket	\N	\N	\N	\N	\N
2274	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2275	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2276	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2277	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2278	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2279	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2280	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2281	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2282	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2283	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2284	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2285	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2286	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2287	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2288	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2289	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2290	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2291	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2292	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2293	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2294	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2295	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2296	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2297	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2298	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2299	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2300	2023-01-01	Familiar Tales	\N	\N	\N	\N	\N
2301	2024-07-09	Familiar Tales	\N	\N	\N	\N	\N
2302	2024-07-09	Familiar Tales	\N	\N	\N	\N	\N
2303	2024-07-10	Familiar Tales	\N	\N	\N	\N	\N
2304	2024-07-12	Familiar Tales	\N	\N	\N	\N	\N
2305	2024-07-13	Familiar Tales	\N	\N	\N	\N	\N
2306	2024-07-18	Familiar Tales	\N	\N	\N	\N	\N
2307	2024-08-12	Familiar Tales	\N	\N	\N	\N	\N
2308	2024-08-13	Familiar Tales	\N	\N	\N	\N	\N
2309	2024-09-22	Familiar Tales	\N	\N	\N	\N	\N
2310	2024-10-12	Familiar Tales	\N	\N	\N	\N	\N
2311	2024-10-19	Familiar Tales	\N	\N	\N	\N	\N
2312	2023-01-01	Flamecraft	\N	\N	\N	\N	\N
2313	2024-01-06	Flamecraft	\N	\N	\N	\N	\N
2314	2024-02-03	Flamecraft	\N	\N	\N	\N	\N
2315	2024-03-23	Flamecraft	\N	\N	\N	\N	\N
2316	2024-03-24	Flamecraft	\N	\N	\N	\N	\N
2317	2024-04-03	Flamecraft	\N	\N	\N	\N	\N
2318	2024-05-12	Flamecraft	\N	\N	\N	\N	\N
2319	2024-06-30	Flamecraft	\N	\N	\N	\N	\N
2320	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2321	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2322	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2323	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2324	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2325	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2326	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2327	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2328	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2329	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2330	2023-01-01	For Northwood!	\N	\N	\N	\N	\N
2331	2024-01-03	Forbidden Desert	\N	\N	\N	\N	\N
2332	2024-01-15	Forbidden Desert	\N	\N	\N	\N	\N
2333	2024-03-03	Forbidden Desert	\N	\N	\N	\N	\N
2334	2024-09-21	Forbidden Desert	\N	\N	\N	\N	\N
2335	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2336	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2337	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2338	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2339	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2340	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2341	2023-01-01	Forbidden Island	\N	\N	\N	\N	\N
2342	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2343	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2344	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2345	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2346	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2347	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2348	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2349	2023-01-01	Forgotten waters	\N	\N	\N	\N	\N
2350	2023-01-01	Geminion	\N	\N	\N	\N	\N
2351	2023-01-01	Geminion	\N	\N	\N	\N	\N
2352	2023-01-01	Geminion	\N	\N	\N	\N	\N
2353	2024-07-09	Geminion	\N	\N	\N	\N	\N
2354	2024-07-09	Geminion	\N	\N	\N	\N	\N
2355	2023-01-01	Ghost fighting treasure hunters	\N	\N	\N	\N	\N
2356	2023-01-01	Ghost fighting treasure hunters	\N	\N	\N	\N	\N
2357	2023-01-01	Gnomes at night	\N	\N	\N	\N	\N
2358	2023-01-01	Gnomes at night	\N	\N	\N	\N	\N
2359	2023-01-01	Gnomes at night	\N	\N	\N	\N	\N
2360	2023-01-01	Gnomes at night	\N	\N	\N	\N	\N
2361	2023-01-01	Great Western Trail	\N	\N	\N	\N	\N
2362	2023-01-01	Great Western Trail	\N	\N	\N	\N	\N
2363	2023-01-01	Great Western Trail	\N	\N	\N	\N	\N
2364	2023-01-01	Great Western Trail	\N	\N	\N	\N	\N
2365	2024-03-30	Great Western Trail	\N	\N	\N	\N	\N
2366	2024-03-31	Great Western Trail	\N	\N	\N	\N	\N
2367	2024-03-31	Great Western Trail	\N	\N	\N	\N	\N
2368	2024-04-02	Great Western Trail	\N	\N	\N	\N	\N
2369	2024-04-03	Great Western Trail	\N	\N	\N	\N	\N
2370	2024-04-04	Great Western Trail	\N	\N	\N	\N	\N
2371	2024-04-05	Great Western Trail	\N	\N	\N	\N	\N
2372	2024-04-05	Great Western Trail	\N	\N	\N	\N	\N
2373	2024-04-06	Great Western Trail	\N	\N	\N	\N	\N
2374	2023-01-01	Hanabi	\N	\N	\N	\N	\N
2375	2023-01-01	Hanabi	\N	\N	\N	\N	\N
2376	2024-08-21	Hanabi	\N	\N	\N	\N	\N
2377	2023-01-01	Hanamikoji	\N	\N	\N	\N	\N
2378	2023-01-01	Hans Teutonica	\N	\N	\N	\N	\N
2379	2024-10-25	happy little dinosaurs	\N	\N	\N	\N	\N
2380	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2381	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2382	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2383	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2384	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2385	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2386	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2387	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2388	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2389	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2390	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2391	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2392	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2393	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2394	2023-01-01	Happy salmon	\N	\N	\N	\N	\N
2395	2024-02-25	Headbanz	\N	\N	\N	\N	\N
2396	2024-05-21	Headbanz	\N	\N	\N	\N	\N
2397	2024-08-18	Headbanz	\N	\N	\N	\N	\N
2398	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2399	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2400	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2401	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2402	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2403	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2404	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2405	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2406	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2407	2023-01-01	Hogwarts Battle	\N	\N	\N	\N	\N
2408	2024-01-06	Hogwarts Battle	\N	\N	\N	\N	\N
2409	2024-02-16	Hogwarts Battle	\N	\N	\N	\N	\N
2410	2024-03-09	Hogwarts Battle	\N	\N	\N	\N	\N
2411	2024-03-23	Hogwarts Battle	\N	\N	\N	\N	\N
2412	2024-05-14	Hogwarts Battle	\N	\N	\N	\N	\N
2413	2024-05-16	Hogwarts Battle	\N	\N	\N	\N	\N
2414	2024-05-16	Hogwarts Battle	\N	\N	\N	\N	\N
2415	2024-05-19	Hogwarts Battle	\N	\N	\N	\N	\N
2416	2024-05-19	Hogwarts Battle	\N	\N	\N	\N	\N
2417	2024-05-22	Hogwarts Battle	\N	\N	\N	\N	\N
2418	2024-05-23	Hogwarts Battle	\N	\N	\N	\N	\N
2419	2024-05-27	Hogwarts Battle	\N	\N	\N	\N	\N
2420	2024-05-29	Hogwarts Battle	\N	\N	\N	\N	\N
2421	2024-05-31	Hogwarts Battle	\N	\N	\N	\N	\N
2422	2024-06-13	Hogwarts Battle	\N	\N	\N	\N	\N
2423	2024-06-22	Hogwarts Battle	\N	\N	\N	\N	\N
2428	2023-01-01	Hotzenplotz	\N	\N	\N	\N	\N
2429	2023-01-01	Hotzenplotz	\N	\N	\N	\N	\N
2430	2023-01-01	Hotzenplotz	\N	\N	\N	\N	\N
2431	2024-05-09	Imperium: Classics	\N	\N	\N	\N	\N
2432	2024-05-10	Imperium: Classics	\N	\N	\N	\N	\N
2433	2024-05-11	Imperium: Classics	\N	\N	\N	\N	\N
2434	2024-05-12	Imperium: Classics	\N	\N	\N	\N	\N
2435	2024-05-13	Imperium: Classics	\N	\N	\N	\N	\N
2436	2024-05-14	Imperium: Classics	\N	\N	\N	\N	\N
2437	2024-05-14	Imperium: Classics	\N	\N	\N	\N	\N
2438	2024-05-15	Imperium: Classics	\N	\N	\N	\N	\N
2439	2024-05-17	Imperium: Classics	\N	\N	\N	\N	\N
2440	2024-05-27	Imperium: Classics	\N	\N	\N	\N	\N
2441	2024-07-23	Imperium: Classics	\N	\N	\N	\N	\N
2442	2024-07-30	Imperium: Classics	\N	\N	\N	\N	\N
2443	2024-09-01	Imperium: Classics	\N	\N	\N	\N	\N
2444	2024-09-15	Imperium: Classics	\N	\N	\N	\N	\N
2445	2024-10-28	Imperium: Classics	\N	\N	\N	\N	\N
2446	2024-01-18	Istanbul	\N	\N	\N	\N	\N
2447	2023-01-01	Karuba	\N	\N	\N	\N	\N
2448	2023-01-01	Karuba	\N	\N	\N	\N	\N
2449	2023-01-01	Karuba	\N	\N	\N	\N	\N
2450	2023-01-01	Karuba	\N	\N	\N	\N	\N
2451	2023-01-01	Karuba	\N	\N	\N	\N	\N
2452	2023-01-01	Karuba	\N	\N	\N	\N	\N
2453	2023-01-01	Karuba	\N	\N	\N	\N	\N
2454	2024-01-08	Karuba	\N	\N	\N	\N	\N
2455	2024-01-27	Karuba	\N	\N	\N	\N	\N
2456	2024-05-14	Karuba	\N	\N	\N	\N	\N
2457	2024-07-06	Karuba	\N	\N	\N	\N	\N
2458	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2459	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2460	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2461	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2462	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2463	2023-01-01	Kingdomino	\N	\N	\N	\N	\N
2464	2024-01-25	Kingdomino	\N	\N	\N	\N	\N
2465	2024-06-20	Kingdomino	\N	\N	\N	\N	\N
2466	2024-10-22	Kingdomino	\N	\N	\N	\N	\N
2467	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2468	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2469	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2470	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2471	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2472	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2473	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2474	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2475	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2476	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2477	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2478	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2479	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2480	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2481	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2482	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2483	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2484	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2485	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2486	2023-01-01	Legacy of yu	\N	\N	\N	\N	\N
2487	2024-03-12	Legacy of yu	\N	\N	\N	\N	\N
2488	2024-03-16	Legacy of yu	\N	\N	\N	\N	\N
2489	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2490	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2491	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2492	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2493	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2494	2023-01-01	Lost ruins of Arnak	\N	\N	\N	\N	\N
2495	2024-01-09	Lost ruins of Arnak	\N	\N	\N	\N	\N
2496	2024-01-10	Lost ruins of Arnak	\N	\N	\N	\N	\N
2497	2024-01-12	Lost ruins of Arnak	\N	\N	\N	\N	\N
2498	2024-01-14	Lost ruins of Arnak	\N	\N	\N	\N	\N
2499	2024-01-22	Lost ruins of Arnak	\N	\N	\N	\N	\N
2500	2024-01-23	Lost ruins of Arnak	\N	\N	\N	\N	\N
2501	2024-02-09	Lost ruins of Arnak	\N	\N	\N	\N	\N
2502	2024-02-10	Lost ruins of Arnak	\N	\N	\N	\N	\N
2503	2024-02-11	Lost ruins of Arnak	\N	\N	\N	\N	\N
2504	2024-02-12	Lost ruins of Arnak	\N	\N	\N	\N	\N
2505	2024-02-13	Lost ruins of Arnak	\N	\N	\N	\N	\N
2506	2024-02-20	Lost ruins of Arnak	\N	\N	\N	\N	\N
2507	2024-02-22	Lost ruins of Arnak	\N	\N	\N	\N	\N
2508	2024-02-27	Lost ruins of Arnak	\N	\N	\N	\N	\N
2509	2024-03-18	Lost ruins of Arnak	\N	\N	\N	\N	\N
2510	2024-03-19	Lost ruins of Arnak	\N	\N	\N	\N	\N
2511	2024-03-23	Lost ruins of Arnak	\N	\N	\N	\N	\N
2512	2024-07-22	Lost ruins of Arnak	\N	\N	\N	\N	\N
2513	2024-06-09	Lost Species	\N	\N	\N	\N	\N
2514	2024-06-10	Lost Species	\N	\N	\N	\N	\N
2515	2023-01-01	Magic Maze	\N	\N	\N	\N	\N
2516	2024-03-18	Magic Maze	\N	\N	\N	\N	\N
2517	2023-01-01	Mancala	\N	\N	\N	\N	\N
2518	2023-01-01	Mancala	\N	\N	\N	\N	\N
2519	2023-01-01	Mancala	\N	\N	\N	\N	\N
2520	2023-01-01	Marvel champions	\N	\N	\N	\N	\N
2521	2023-01-01	Marvel champions	\N	\N	\N	\N	\N
2522	2023-01-01	Marvel champions	\N	\N	\N	\N	\N
2523	2024-01-30	Marvel champions	\N	\N	\N	\N	\N
2524	2024-01-31	Marvel champions	\N	\N	\N	\N	\N
2525	2024-02-01	Marvel champions	\N	\N	\N	\N	\N
2526	2024-05-31	Marvel champions	\N	\N	\N	\N	\N
2527	2023-01-01	Micro Macro	\N	\N	\N	\N	\N
2528	2023-01-01	Micro Macro	\N	\N	\N	\N	\N
2529	2023-01-01	Micro Macro	\N	\N	\N	\N	\N
2530	2023-01-01	Micro Macro	\N	\N	\N	\N	\N
2531	2023-01-01	Micro Macro	\N	\N	\N	\N	\N
2532	2024-06-01	Micro Macro	\N	\N	\N	\N	\N
2533	2023-01-01	Meadow	\N	\N	\N	\N	\N
2534	2023-01-01	Meadow	\N	\N	\N	\N	\N
2535	2023-01-01	Meadow	\N	\N	\N	\N	\N
2536	2023-01-01	Meadow	\N	\N	\N	\N	\N
2537	2023-01-01	Meadow	\N	\N	\N	\N	\N
2538	2023-01-01	Meadow	\N	\N	\N	\N	\N
2539	2024-01-22	Meadow	\N	\N	\N	\N	\N
2540	2024-02-10	Meadow	\N	\N	\N	\N	\N
2541	2024-03-10	Meadow	\N	\N	\N	\N	\N
2542	2024-04-28	Meadow	\N	\N	\N	\N	\N
2543	2024-06-25	Meadow	\N	\N	\N	\N	\N
2544	2023-01-01	Memory	\N	\N	\N	\N	\N
2545	2023-01-01	Memory	\N	\N	\N	\N	\N
2546	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2547	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2548	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2549	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2550	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2551	2023-01-01	Monopoly Deal	\N	\N	\N	\N	\N
2552	2024-04-29	Monopoly Deal	\N	\N	\N	\N	\N
2553	2024-05-22	Monopoly Deal	\N	\N	\N	\N	\N
2554	2024-05-23	Monopoly Deal	\N	\N	\N	\N	\N
2555	2024-05-23	Monopoly Deal	\N	\N	\N	\N	\N
2556	2024-05-24	Monopoly Deal	\N	\N	\N	\N	\N
2557	2024-08-07	Monopoly Deal	\N	\N	\N	\N	\N
2558	2024-08-08	Monopoly Deal	\N	\N	\N	\N	\N
2559	2024-08-14	Monopoly Deal	\N	\N	\N	\N	\N
2560	2024-08-26	Monopoly Deal	\N	\N	\N	\N	\N
2561	2024-10-02	Monopoly Deal	\N	\N	\N	\N	\N
2562	2024-10-03	Monopoly Deal	\N	\N	\N	\N	\N
2563	2023-01-01	Mr Jack	\N	\N	\N	\N	\N
2564	2023-01-01	Mr Jack	\N	\N	\N	\N	\N
2565	2023-01-01	Mr Jack	\N	\N	\N	\N	\N
2566	2023-01-01	Mt Kilajava	\N	\N	\N	\N	\N
2567	2023-01-01	Mystic Vale	\N	\N	\N	\N	\N
2568	2023-01-01	Mystic Vale	\N	\N	\N	\N	\N
2569	2023-01-01	Mystic Vale	\N	\N	\N	\N	\N
2570	2024-05-14	Mystic Vale	\N	\N	\N	\N	\N
2571	2024-10-23	Mystic Vale	\N	\N	\N	\N	\N
2572	2023-01-01	Old maid	\N	\N	\N	\N	\N
2573	2023-01-01	Old maid	\N	\N	\N	\N	\N
2574	2023-01-01	Old maid	\N	\N	\N	\N	\N
2575	2023-01-01	Onitama	\N	\N	\N	\N	\N
2576	2023-01-01	Once upon a time	\N	\N	\N	\N	\N
2577	2023-01-01	Once upon a time	\N	\N	\N	\N	\N
2578	2023-01-01	Outfoxed	\N	\N	\N	\N	\N
2579	2023-01-01	Outfoxed	\N	\N	\N	\N	\N
2580	2023-01-01	Outfoxed	\N	\N	\N	\N	\N
2581	2024-07-14	Outfoxed	\N	\N	\N	\N	\N
2582	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2583	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2584	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2585	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2586	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2587	2023-01-01	Pacific Ocean	\N	\N	\N	\N	\N
2588	2024-05-16	Pacific Ocean	\N	\N	\N	\N	\N
2589	2024-05-21	Pacific Ocean	\N	\N	\N	\N	\N
2590	2024-05-22	Pacific Ocean	\N	\N	\N	\N	\N
2591	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2592	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2593	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2594	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2595	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2596	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2597	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2598	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2599	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2600	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2601	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2602	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2603	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2604	2023-01-01	Pandemic Legacy: Season 1	\N	\N	\N	\N	\N
2605	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2606	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2607	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2608	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2609	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2610	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2611	2023-01-01	Pass the party food	\N	\N	\N	\N	\N
2612	2024-05-28	Pass the party food	\N	\N	\N	\N	\N
2613	2023-01-01	Pictures	\N	\N	\N	\N	\N
2614	2023-01-01	Pictures	\N	\N	\N	\N	\N
2615	2023-01-01	Pictures	\N	\N	\N	\N	\N
2616	2023-01-01	Pictures	\N	\N	\N	\N	\N
2617	2023-01-01	Pictures	\N	\N	\N	\N	\N
2618	2023-01-01	Planet	\N	\N	\N	\N	\N
2619	2023-01-01	Planet	\N	\N	\N	\N	\N
2620	2023-01-01	Planet	\N	\N	\N	\N	\N
2621	2023-01-01	Planet	\N	\N	\N	\N	\N
2622	2023-01-01	Planet	\N	\N	\N	\N	\N
2623	2023-01-01	Planet	\N	\N	\N	\N	\N
2624	2023-01-01	Planet	\N	\N	\N	\N	\N
2625	2024-06-21	Planet	\N	\N	\N	\N	\N
2626	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2627	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2628	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2629	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2630	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2631	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2632	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2633	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2634	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2635	2023-01-01	Pokemon	\N	\N	\N	\N	\N
2636	2024-01-09	Pokemon	\N	\N	\N	\N	\N
2637	2024-01-13	Pokemon	\N	\N	\N	\N	\N
2638	2024-01-14	Pokemon	\N	\N	\N	\N	\N
2639	2024-01-16	Pokemon	\N	\N	\N	\N	\N
2640	2024-01-17	Pokemon	\N	\N	\N	\N	\N
2641	2024-01-20	Pokemon	\N	\N	\N	\N	\N
2642	2024-01-22	Pokemon	\N	\N	\N	\N	\N
2643	2024-01-27	Pokemon	\N	\N	\N	\N	\N
2644	2024-01-29	Pokemon	\N	\N	\N	\N	\N
2645	2024-02-02	Pokemon	\N	\N	\N	\N	\N
2646	2024-02-04	Pokemon	\N	\N	\N	\N	\N
2647	2024-02-10	Pokemon	\N	\N	\N	\N	\N
2648	2024-03-01	Pokemon	\N	\N	\N	\N	\N
2649	2024-03-05	Pokemon	\N	\N	\N	\N	\N
2650	2024-03-20	Pokemon	\N	\N	\N	\N	\N
2651	2024-03-22	Pokemon	\N	\N	\N	\N	\N
2652	2024-03-28	Pokemon	\N	\N	\N	\N	\N
2653	2024-03-29	Pokemon	\N	\N	\N	\N	\N
2654	2024-03-29	Pokemon	\N	\N	\N	\N	\N
2655	2024-03-30	Pokemon	\N	\N	\N	\N	\N
2656	2024-03-31	Pokemon	\N	\N	\N	\N	\N
2657	2024-03-31	Pokemon	\N	\N	\N	\N	\N
2658	2024-04-01	Pokemon	\N	\N	\N	\N	\N
2659	2024-04-01	Pokemon	\N	\N	\N	\N	\N
2660	2024-04-02	Pokemon	\N	\N	\N	\N	\N
2661	2024-04-02	Pokemon	\N	\N	\N	\N	\N
2662	2024-04-06	Pokemon	\N	\N	\N	\N	\N
2663	2024-04-06	Pokemon	\N	\N	\N	\N	\N
2664	2024-04-12	Pokemon	\N	\N	\N	\N	\N
2665	2024-04-13	Pokemon	\N	\N	\N	\N	\N
2666	2024-04-26	Pokemon	\N	\N	\N	\N	\N
2667	2024-04-27	Pokemon	\N	\N	\N	\N	\N
2668	2024-04-28	Pokemon	\N	\N	\N	\N	\N
2669	2024-04-29	Pokemon	\N	\N	\N	\N	\N
2670	2024-05-12	Pokemon	\N	\N	\N	\N	\N
2671	2024-05-12	Pokemon	\N	\N	\N	\N	\N
2672	2024-05-14	Pokemon	\N	\N	\N	\N	\N
2673	2024-05-19	Pokemon	\N	\N	\N	\N	\N
2674	2024-05-20	Pokemon	\N	\N	\N	\N	\N
2675	2024-05-20	Pokemon	\N	\N	\N	\N	\N
2676	2024-05-21	Pokemon	\N	\N	\N	\N	\N
2677	2024-05-22	Pokemon	\N	\N	\N	\N	\N
2678	2024-05-23	Pokemon	\N	\N	\N	\N	\N
2679	2024-05-29	Pokemon	\N	\N	\N	\N	\N
2680	2024-05-31	Pokemon	\N	\N	\N	\N	\N
2681	2024-05-31	Pokemon	\N	\N	\N	\N	\N
2682	2024-06-24	Pokemon	\N	\N	\N	\N	\N
2683	2024-06-24	Pokemon	\N	\N	\N	\N	\N
2684	2024-06-30	Pokemon	\N	\N	\N	\N	\N
2685	2024-08-08	Pokemon	\N	\N	\N	\N	\N
2686	2024-08-08	Pokemon	\N	\N	\N	\N	\N
2687	2024-08-25	Pokemon	\N	\N	\N	\N	\N
2688	2024-10-26	Pokemon	\N	\N	\N	\N	\N
2689	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2690	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2691	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2692	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2693	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2694	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2695	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2696	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2697	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2698	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2699	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2700	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2701	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2702	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2703	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2704	2023-01-01	Pokémon: my first battle	\N	\N	\N	\N	\N
2705	2024-01-29	Pokémon: my first battle	\N	\N	\N	\N	\N
2706	2024-01-30	Pokémon: my first battle	\N	\N	\N	\N	\N
2707	2024-02-04	Pokémon: my first battle	\N	\N	\N	\N	\N
2708	2024-02-10	Pokémon: my first battle	\N	\N	\N	\N	\N
2709	2024-03-02	Pokémon: my first battle	\N	\N	\N	\N	\N
2710	2024-03-03	Pokémon: my first battle	\N	\N	\N	\N	\N
2711	2024-03-17	Pokémon: my first battle	\N	\N	\N	\N	\N
2712	2024-03-24	Pokémon: my first battle	\N	\N	\N	\N	\N
2713	2024-03-31	Pokémon: my first battle	\N	\N	\N	\N	\N
2714	2024-05-23	Pokémon: my first battle	\N	\N	\N	\N	\N
2715	2024-08-25	Pokémon: my first battle	\N	\N	\N	\N	\N
2716	2024-10-12	Pokémon: my first battle	\N	\N	\N	\N	\N
2717	2023-01-01	Poo	\N	\N	\N	\N	\N
2718	2023-01-01	Poo	\N	\N	\N	\N	\N
2719	2023-01-01	Poo	\N	\N	\N	\N	\N
2720	2023-01-01	Poo	\N	\N	\N	\N	\N
2721	2023-01-01	Poo	\N	\N	\N	\N	\N
2722	2023-01-01	Poo	\N	\N	\N	\N	\N
2723	2023-01-01	Poo	\N	\N	\N	\N	\N
2724	2023-01-01	Poo	\N	\N	\N	\N	\N
2725	2023-01-01	Poo	\N	\N	\N	\N	\N
2726	2023-01-01	Poo	\N	\N	\N	\N	\N
2727	2023-01-01	Poo	\N	\N	\N	\N	\N
2728	2023-01-01	Poo	\N	\N	\N	\N	\N
2729	2023-01-01	Poo	\N	\N	\N	\N	\N
2730	2023-01-01	Poo	\N	\N	\N	\N	\N
2731	2024-09-28	Poo	\N	\N	\N	\N	\N
2732	2024-10-25	Poo	\N	\N	\N	\N	\N
2733	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2734	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2735	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2736	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2737	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2738	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2739	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2740	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2741	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2742	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2743	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2744	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2745	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2746	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2747	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2748	2023-01-01	Poo Bingo	\N	\N	\N	\N	\N
2749	2024-08-04	Poo Bingo	\N	\N	\N	\N	\N
2750	2024-10-25	Poo Bingo	\N	\N	\N	\N	\N
2751	2023-01-01	Project L	\N	\N	\N	\N	\N
2752	2023-01-01	Project L	\N	\N	\N	\N	\N
2753	2023-01-01	Project L	\N	\N	\N	\N	\N
2754	2023-01-01	Project L	\N	\N	\N	\N	\N
2755	2023-01-01	Project L	\N	\N	\N	\N	\N
2756	2023-01-01	Project L	\N	\N	\N	\N	\N
2757	2023-01-01	Project L	\N	\N	\N	\N	\N
2758	2023-01-01	Project L	\N	\N	\N	\N	\N
2759	2023-01-01	Project L	\N	\N	\N	\N	\N
2760	2024-01-27	Project L	\N	\N	\N	\N	\N
2761	2024-02-17	Project L	\N	\N	\N	\N	\N
2762	2024-05-31	Project L	\N	\N	\N	\N	\N
2763	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2764	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2765	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2766	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2767	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2768	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2769	2023-01-01	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2770	2024-01-12	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2771	2024-01-14	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2772	2024-01-16	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2773	2024-03-17	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2774	2024-03-29	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2775	2024-04-27	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2776	2024-05-18	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2777	2024-06-21	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2778	2024-07-10	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2779	2024-07-15	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2780	2024-07-20	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2781	2024-07-21	Quacks of Quendlinburg	\N	\N	\N	\N	\N
2782	2024-01-06	Race for the galaxy	\N	\N	\N	\N	\N
2783	2024-02-02	Race for the galaxy	\N	\N	\N	\N	\N
2784	2024-02-02	Race for the galaxy	\N	\N	\N	\N	\N
2785	2024-02-10	Race for the galaxy	\N	\N	\N	\N	\N
2786	2024-02-17	Race for the galaxy	\N	\N	\N	\N	\N
2787	2024-04-27	Race for the galaxy	\N	\N	\N	\N	\N
2788	2024-05-05	Race for the galaxy	\N	\N	\N	\N	\N
2789	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2790	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2791	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2792	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2793	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2794	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2795	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2796	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2797	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2798	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2799	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2800	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2801	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2802	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2803	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2804	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2805	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2806	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2807	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2808	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2809	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2810	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2811	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2812	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2813	2023-01-01	Rat a tat cat	\N	\N	\N	\N	\N
2814	2023-01-01	Rhino Hero: Super Battle	\N	\N	\N	\N	\N
2815	2023-01-01	Rhino Hero: Super Battle	\N	\N	\N	\N	\N
2816	2024-07-25	Rhino Hero: Super Battle	\N	\N	\N	\N	\N
2817	2023-01-01	The Robber Hotzenplotz	\N	\N	\N	\N	\N
2818	2023-01-01	The Robber Hotzenplotz	\N	\N	\N	\N	\N
2819	2023-01-01	The Robber Hotzenplotz	\N	\N	\N	\N	\N
2820	2023-01-01	The Robber Hotzenplotz	\N	\N	\N	\N	\N
2821	2023-01-01	Roll & Meow	\N	\N	\N	\N	\N
2822	2024-04-29	Rummikub	\N	\N	\N	\N	\N
2823	2024-05-01	Rummikub	\N	\N	\N	\N	\N
2824	2024-05-03	Rummikub	\N	\N	\N	\N	\N
2825	2024-05-05	Rummikub	\N	\N	\N	\N	\N
2826	2024-05-31	Rummikub	\N	\N	\N	\N	\N
2827	2024-06-30	Rummikub	\N	\N	\N	\N	\N
2828	2024-07-13	Rummikub	\N	\N	\N	\N	\N
2829	2024-09-28	Rummikub	\N	\N	\N	\N	\N
2830	2024-09-29	Rummikub	\N	\N	\N	\N	\N
2831	2024-09-30	Rummikub	\N	\N	\N	\N	\N
2832	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2833	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2834	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2835	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2836	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2837	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2838	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2839	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2840	2023-01-01	Saboteur	\N	\N	\N	\N	\N
2841	2024-08-04	Saboteur	\N	\N	\N	\N	\N
2842	2024-08-04	Saboteur	\N	\N	\N	\N	\N
2843	2024-08-06	Saboteur	\N	\N	\N	\N	\N
2844	2024-08-11	Saboteur	\N	\N	\N	\N	\N
2845	2024-09-29	Saboteur	\N	\N	\N	\N	\N
2846	2023-01-01	Santa's workshop	\N	\N	\N	\N	\N
2847	2023-01-01	Santorini	\N	\N	\N	\N	\N
2848	2023-01-01	Santorini	\N	\N	\N	\N	\N
2849	2023-01-01	Santorini	\N	\N	\N	\N	\N
2850	2023-01-01	Santorini	\N	\N	\N	\N	\N
2851	2024-02-10	Santorini	\N	\N	\N	\N	\N
2852	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2853	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2854	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2855	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2856	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2857	2023-01-01	SCOUT	\N	\N	\N	\N	\N
2858	2024-06-01	SCOUT	\N	\N	\N	\N	\N
2859	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2860	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2861	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2862	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2863	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2864	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2865	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2866	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2867	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2868	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2869	2023-01-01	Scribbly Gum	\N	\N	\N	\N	\N
2870	2024-01-24	Scribbly Gum	\N	\N	\N	\N	\N
2871	2024-03-05	Scribbly Gum	\N	\N	\N	\N	\N
2872	2024-05-17	Scribbly Gum	\N	\N	\N	\N	\N
2873	2024-05-28	Scribbly Gum	\N	\N	\N	\N	\N
2874	2024-06-01	Scribbly Gum	\N	\N	\N	\N	\N
2875	2023-01-01	Scythe	\N	\N	\N	\N	\N
2876	2023-01-01	Scythe	\N	\N	\N	\N	\N
2877	2023-01-01	Scythe	\N	\N	\N	\N	\N
2878	2023-01-01	The Search for planet X	\N	\N	\N	\N	\N
2879	2024-04-03	The Search for planet X	\N	\N	\N	\N	\N
2880	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2881	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2882	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2883	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2884	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2885	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2886	2023-01-01	The Shivers	\N	\N	\N	\N	\N
2887	2023-01-01	Sleeping Gods	\N	\N	\N	\N	\N
2888	2023-01-01	Sleeping Gods	\N	\N	\N	\N	\N
2889	2023-01-01	Sleeping Gods	\N	\N	\N	\N	\N
2890	2023-01-01	Sleeping Gods	\N	\N	\N	\N	\N
2891	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2892	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2893	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2894	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2895	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2896	2023-01-01	Sleeping Queens	\N	\N	\N	\N	\N
2897	2024-01-03	Sleeping Queens	\N	\N	\N	\N	\N
2898	2024-04-14	Sleeping Queens	\N	\N	\N	\N	\N
2899	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2900	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2901	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2902	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2903	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2904	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2905	2023-01-01	Sleeping Queens 2	\N	\N	\N	\N	\N
2906	2024-04-14	Sleeping Queens 2	\N	\N	\N	\N	\N
2907	2024-06-17	Sleeping Queens 2	\N	\N	\N	\N	\N
2908	2024-08-08	Sleeping Queens 2	\N	\N	\N	\N	\N
2909	2024-04-16	Splendour (Pokémon)	\N	\N	\N	\N	\N
2910	2024-04-18	Splendour (Pokémon)	\N	\N	\N	\N	\N
2911	2024-04-22	Splendour (Pokémon)	\N	\N	\N	\N	\N
2912	2024-04-23	Splendour (Pokémon)	\N	\N	\N	\N	\N
2913	2024-04-23	Splendour (Pokémon)	\N	\N	\N	\N	\N
2914	2024-04-26	Splendour (Pokémon)	\N	\N	\N	\N	\N
2915	2024-04-28	Splendour (Pokémon)	\N	\N	\N	\N	\N
2916	2024-04-29	Splendour (Pokémon)	\N	\N	\N	\N	\N
2917	2024-05-11	Splendour (Pokémon)	\N	\N	\N	\N	\N
2918	2024-06-14	Splendour (Pokémon)	\N	\N	\N	\N	\N
2919	2024-06-15	Splendour (Pokémon)	\N	\N	\N	\N	\N
2920	2024-06-21	Splendour (Pokémon)	\N	\N	\N	\N	\N
2921	2024-08-18	Splendour (Pokémon)	\N	\N	\N	\N	\N
2922	2024-08-22	Splendour (Pokémon)	\N	\N	\N	\N	\N
2923	2024-08-24	Splendour (Pokémon)	\N	\N	\N	\N	\N
2924	2024-09-17	Splendour (Pokémon)	\N	\N	\N	\N	\N
2925	2024-10-13	Spirit Island	\N	\N	\N	\N	\N
2926	2024-10-13	Spirit Island	\N	\N	\N	\N	\N
2927	2024-10-15	Spirit Island	\N	\N	\N	\N	\N
2928	2024-10-19	Spirit Island	\N	\N	\N	\N	\N
2929	2024-10-22	Spirit Island	\N	\N	\N	\N	\N
2930	2024-10-25	Spirit Island	\N	\N	\N	\N	\N
2932	2023-01-01	Stone Age	\N	\N	\N	\N	\N
2933	2023-01-01	Stone Age: My First	\N	\N	\N	\N	\N
2934	2023-01-01	Stone Age: My First	\N	\N	\N	\N	\N
2935	2023-01-01	Stone Age: My First	\N	\N	\N	\N	\N
2936	2024-08-23	Stone Age: My First	\N	\N	\N	\N	\N
2937	2023-01-01	Stuffed Fables	\N	\N	\N	\N	\N
2938	2023-01-01	Stuffed Fables	\N	\N	\N	\N	\N
2939	2023-01-01	Sushi Go	\N	\N	\N	\N	\N
2940	2023-01-01	Sushi Go	\N	\N	\N	\N	\N
2941	2023-01-01	Sushi Go	\N	\N	\N	\N	\N
2942	2024-07-14	Sushi Go	\N	\N	\N	\N	\N
2943	2024-08-21	Sushi Go	\N	\N	\N	\N	\N
2944	2024-09-29	Taco cat goat ...	\N	\N	\N	\N	\N
2945	2024-09-30	Taco cat goat ...	\N	\N	\N	\N	\N
2946	2024-10-01	Taco cat goat ...	\N	\N	\N	\N	\N
2947	2024-10-03	Taco cat goat ...	\N	\N	\N	\N	\N
2948	2024-10-04	Taco cat goat ...	\N	\N	\N	\N	\N
2949	2023-01-01	Targi	\N	\N	\N	\N	\N
2950	2024-03-24	Targi	\N	\N	\N	\N	\N
2951	2023-01-01	Ticket to Ride: First Journey	\N	\N	\N	\N	\N
2952	2023-01-01	Ticket to Ride: First Journey	\N	\N	\N	\N	\N
2953	2023-01-01	Ticket to Ride: First Journey	\N	\N	\N	\N	\N
2954	2024-04-09	Ticket to Ride: First Journey	\N	\N	\N	\N	\N
2955	2024-08-07	Ticket to Ride: First Journey	\N	\N	\N	\N	\N
2956	2023-01-01	Tiny Towns	\N	\N	\N	\N	\N
2957	2023-01-01	Tiny Towns	\N	\N	\N	\N	\N
2958	2024-07-16	Tiny Towns	\N	\N	\N	\N	\N
2959	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2960	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2961	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2962	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2963	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2964	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2965	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2966	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2967	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2968	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2969	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2970	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2971	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2972	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2973	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2974	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2975	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2976	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2977	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2978	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2979	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2980	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2981	2023-01-01	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2982	2024-05-20	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2983	2024-08-04	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2984	2024-09-13	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2985	2024-09-17	Top Trump: Dinosaurs	\N	\N	\N	\N	\N
2986	2023-01-01	Top Trump: Harry Potter	\N	\N	\N	\N	\N
2987	2023-01-01	Top Trump: Harry Potter	\N	\N	\N	\N	\N
2988	2024-05-21	Top Trump: Harry Potter	\N	\N	\N	\N	\N
2989	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2990	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2991	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2992	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2993	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2994	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2995	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2996	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2997	2023-01-01	Top trumps: Stat Attack	\N	\N	\N	\N	\N
2998	2023-01-01	Unlock!: Heroic Adventures	\N	\N	\N	\N	\N
2999	2023-01-01	Unlock!: Heroic Adventures	\N	\N	\N	\N	\N
3000	2023-01-01	Unlock! Kids: Detetective Stories	\N	\N	\N	\N	\N
3001	2023-01-01	Unlock! Kids: Detetective Stories	\N	\N	\N	\N	\N
3002	2023-01-01	Unlock! Kids: Detetective Stories	\N	\N	\N	\N	\N
3003	2023-01-01	Unlock! Kids: Detetective Stories	\N	\N	\N	\N	\N
3004	2024-01-03	Unstable Unicorns: Travel	\N	\N	\N	\N	\N
3005	2024-07-14	Unstable Unicorns: Travel	\N	\N	\N	\N	\N
3006	2023-01-01	UNO	\N	\N	\N	\N	\N
3007	2023-01-01	UNO	\N	\N	\N	\N	\N
3008	2023-01-01	UNO	\N	\N	\N	\N	\N
3009	2023-01-01	UNO	\N	\N	\N	\N	\N
3010	2023-01-01	UNO	\N	\N	\N	\N	\N
3011	2023-01-01	UNO	\N	\N	\N	\N	\N
3012	2023-01-01	UNO	\N	\N	\N	\N	\N
3013	2023-01-01	UNO	\N	\N	\N	\N	\N
3014	2023-01-01	UNO	\N	\N	\N	\N	\N
3015	2023-01-01	UNO	\N	\N	\N	\N	\N
3016	2023-01-01	UNO	\N	\N	\N	\N	\N
3017	2024-04-29	UNO	\N	\N	\N	\N	\N
3018	2024-08-18	UNO	\N	\N	\N	\N	\N
3019	2023-01-01	Valley of the Vikings	\N	\N	\N	\N	\N
3020	2023-01-01	Valley of the Vikings	\N	\N	\N	\N	\N
3021	2023-01-01	Valley of the Vikings	\N	\N	\N	\N	\N
3022	2024-03-05	Valley of the Vikings	\N	\N	\N	\N	\N
3023	2023-01-01	Voyages	\N	\N	\N	\N	\N
3024	2023-01-01	Waypoints	\N	\N	\N	\N	\N
3025	2023-01-01	Waypoints	\N	\N	\N	\N	\N
3026	2023-01-01	Wingspan	\N	\N	\N	\N	\N
3027	2023-01-01	Wingspan	\N	\N	\N	\N	\N
3028	2023-01-01	Wingspan	\N	\N	\N	\N	\N
3029	2023-01-01	Wingspan	\N	\N	\N	\N	\N
3030	2024-02-05	Wingspan	\N	\N	\N	\N	\N
3031	2023-01-01	Yahtzee	\N	\N	\N	\N	\N
1973	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1974	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1975	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1976	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1977	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1978	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1979	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1980	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1981	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1982	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1983	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1984	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1985	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1986	2023-01-01	Ark Nova	\N	\N	\N	\N	\N
1987	2024-01-02	Ark Nova	\N	\N	\N	\N	\N
1988	2024-01-03	Ark Nova	\N	\N	\N	\N	\N
1989	2024-01-07	Ark Nova	\N	\N	\N	\N	\N
1990	2024-01-13	Ark Nova	\N	\N	\N	\N	\N
1991	2024-01-16	Ark Nova	\N	\N	\N	\N	\N
1992	2024-01-28	Ark Nova	\N	\N	\N	\N	\N
1993	2024-01-29	Ark Nova	\N	\N	\N	\N	\N
1994	2024-01-30	Ark Nova	\N	\N	\N	\N	\N
1995	2024-02-07	Ark Nova	\N	\N	\N	\N	\N
1996	2024-02-07	Ark Nova	\N	\N	\N	\N	\N
1997	2024-02-08	Ark Nova	\N	\N	\N	\N	\N
1998	2024-02-08	Ark Nova	\N	\N	\N	\N	\N
1999	2024-02-14	Ark Nova	\N	\N	\N	\N	\N
2000	2024-02-14	Ark Nova	\N	\N	\N	\N	\N
2001	2024-02-16	Ark Nova	\N	\N	\N	\N	\N
2002	2024-02-18	Ark Nova	\N	\N	\N	\N	\N
2003	2024-02-23	Ark Nova	\N	\N	\N	\N	\N
2004	2024-03-21	Ark Nova	\N	\N	\N	\N	\N
2005	2024-03-25	Ark Nova	\N	\N	\N	\N	\N
2006	2024-04-28	Ark Nova	\N	\N	\N	\N	\N
2007	2024-05-07	Ark Nova	\N	\N	\N	\N	\N
2008	2024-08-01	Ark Nova	\N	\N	\N	\N	\N
2009	2024-08-02	Ark Nova	\N	\N	\N	\N	\N
2010	2024-08-15	Ark Nova	\N	\N	\N	\N	\N
2011	2024-09-01	Ark Nova	\N	\N	\N	\N	\N
2424	2024-03-13	Horizons of Spirit Island	\N	\N	\N	\N	\N
2425	2024-05-01	Horizons of Spirit Island	\N	\N	\N	\N	\N
2426	2024-05-16	Horizons of Spirit Island	\N	\N	\N	\N	\N
2427	2024-05-29	Horizons of Spirit Island	\N	\N	\N	\N	\N
3032	2024-10-29	7 Wonders	\N	\N	\N	\N	\N
2012	2024-09-17	Ark Nova	Map A, start 10	\N	\N	\N	\N
3095	2024-11-19	Ark Nova		\N	\N	\N	\N
2931	2024-10-26	Spirit Island	Flickering Shadow	\N	\N	\N	\N
3034	2024-10-30	Cascadia		\N	\N	\N	\N
3035	2024-10-30	Rummikub		\N	\N	\N	\N
3036	2024-10-30	Cards: 500		\N	\N	\N	\N
3037	2024-10-30	Familiar Tales		\N	\N	\N	\N
3038	2024-10-31	Spirit Island		\N	\N	\N	\N
3039	2024-11-01	Azul		\N	\N	\N	\N
3042	2024-11-03	For Northwood!		\N	\N	\N	\N
3048	2024-11-04	Taco cat goat ...		\N	\N	\N	\N
3049	2024-11-06	Sushi Go		\N	\N	\N	\N
3050	2024-11-06	Sleeping Queens		\N	\N	\N	\N
3051	2024-11-06	Spirit Island		\N	\N	\N	\N
3052	2024-11-06	7 Wonders		\N	\N	\N	\N
3053	2024-11-06	Hotzenplotz		\N	\N	\N	\N
3057	2024-11-06	Spirit Island		\N	\N	\N	\N
3060	2024-11-09	Spirit Island		\N	\N	\N	\N
3061	2024-11-09	Pass the party food		\N	\N	\N	\N
3062	2024-11-09	Dragon Parks		\N	\N	\N	\N
3063	2024-11-09	Draftosaurus		\N	\N	\N	\N
3064	2024-11-09	Sleeping Queens 2		\N	\N	\N	\N
3065	2024-11-09	Scribbly Gum		\N	\N	\N	\N
3066	2024-11-09	Cascadia		\N	\N	\N	\N
3067	2024-11-10	Spirit Island	Start shadows flicker again from scratch	\N	\N	\N	\N
3068	2024-11-10	Busy Beaks		\N	\N	\N	\N
3069	2024-11-10	7 Wonders		\N	\N	\N	\N
3070	2024-11-12	7 Wonders		\N	\N	\N	\N
3071	2024-11-13	7 Wonders		\N	\N	\N	\N
3072	2024-11-14	7 Wonders		\N	\N	\N	\N
3073	2024-11-14	Quacks of Quendlinburg		\N	\N	\N	\N
3074	2024-11-14	Forbidden Island		\N	\N	\N	\N
3075	2024-11-14	Spirit Island		\N	\N	\N	\N
3077	2024-11-15	7 Wonders		\N	\N	\N	\N
3078	2024-11-15	Familiar Tales		\N	\N	\N	\N
3079	2024-11-15	Cascadia		\N	\N	\N	\N
3080	2024-11-15	Cascadia		\N	\N	\N	\N
3082	2024-11-16	Familiar Tales		\N	\N	\N	\N
3083	2024-11-16	Bah Humbug		\N	\N	\N	\N
3096	2024-11-20	Ark Nova	Won map A, start 10 appeal 	\N	\N	\N	\N
3084	2024-11-17	Spirit Island	Current game: A spread of rampant green	\N	\N	\N	\N
3086	2024-11-17	Scribbly Gum		\N	\N	\N	\N
3087	2024-11-17	7 Wonders		\N	\N	\N	\N
3088	2024-11-17	Sleeping Queens 2		\N	\N	\N	\N
3089	2024-11-17	Sleeping Queens		\N	\N	\N	\N
3090	2024-11-18	7 Wonders		\N	\N	\N	\N
3091	2024-11-18	Kingdomino		\N	\N	\N	\N
3076	2024-11-15	Spirit Island	Won shadows flicker like flame	\N	\N	\N	\N
3033	2024-10-29	Imperium: Classics	Level 1: Roman (me) Verus Greek (AI)	\N	\N	\N	\N
3085	2024-11-17	Catan		\N	\N	\N	\N
3092	2024-11-18	Spirit Island		\N	\N	\N	\N
3093	2024-11-19	Spirit Island	Won a spread of rampant green	\N	\N	\N	\N
3094	2024-11-19	The Bears and the Bees		\N	\N	\N	\N
3097	2024-11-20	Imperium: Classics		\N	\N	\N	\N
3099	2024-11-23	Imperium: Classics	Roman (me) vs Greek (bot).	Lost	71	81	Imperator. Romans (me) versus Greek (bot).
3101	2024-11-22	Tussie Mussie		\N	\N	\N	\N
3102	2024-11-23	Tussie Mussie		\N	\N	\N	\N
3103	2024-11-23	Tussie Mussie		\N	\N	\N	\N
3104	2024-11-23	7 Wonders		\N	\N	\N	\N
3105	2024-11-23	Catan		\N	\N	\N	\N
3098	2024-11-21	Imperium: Classics	Try again. Bot gained lots of attach cards	Lost	70	100	Imperator. Romans (me) versus Greek (bot).
3081	2024-11-16	Cascadia	 	\N	\N	\N	\N
3109	2024-11-23	7 Wonders					\N
3110	2024-11-23	Karuba					\N
3112	2024-11-24	Century: Spice Road					\N
3100	2024-11-23	Imperium: Classics	\N	\N	\N	\N	\N
3111	2024-11-24	Imperium: Classics	Bots Turn				\N
3115	2024-11-25	Imperium: Classics	Romans (me) vs Greeks (bot)	Won	91	77	Imperator. Romans (me) versus Greek (bot).
3114	2024-11-24	Imperium: Classics	Bots Turn				
3116	2024-11-26	Taco cat goat ...					
3117	2024-11-26	Tussie Mussie					
3118	2024-11-27	Wingspan		Won	101	93	Medium (multiply by 4)
3119	2024-11-27	Tussie Mussie					
3120	2024-11-27	Tussie Mussie					
3121	2024-11-27	Quacks of Quendlinburg					
3122	2024-11-28	Ares Expedition 					
3124	2024-11-30	Everdell: My Lil'					
3125	2024-11-30	Valley of the Vikings					
3126	2024-11-30	Coconuts					
3127	2024-11-30	Santa's workshop					
3128	2024-11-30	Bah Humbug					
3129	2024-11-30	Bah Humbug					
3130	2024-12-04	Bah Humbug					
3131	2024-12-01	Bah Humbug					
3132	2024-12-06	Ares Expedition 	Oxygen: 14, temp:-6, 4 ocean tiles uncovered, TR: 27, trees: 4	Lost			Novice
3133	2024-12-07	Spirit Island	Start of my turn. 				
3134	2024-12-07	Deck the halls					
3135	2024-12-07	Bah Humbug					
3136	2024-12-07	7 Wonders					
3138	2024-12-08	Familiar Tales	Completed page 63				
3139	2024-12-08	The Crew: Mission Deep Sea					
3140	2024-12-08	Deck the halls					
3186	2024-12-30	Imperium: Classics	Romans (me) vs Persians (bot). Next challenge - carthagians	Won	103	73	Imperator. Romans (me) vs Persians (bot).
3123	2024-11-30	Cascadia	Onto scenario 2	Won	84		Scenario 1
3141	2024-12-08	Deck the halls					
3143	2024-12-08	Bohnanza: Wūrfel					
3137	2024-12-08	Spirit Island	Spirit: Thunderspeaker.\n Pretty close. \nLost on blight.				
3144	2024-12-08	Spirit Island	Spirit: Thunderspeaker.\n Pretty close. \nLost on blight.	Lost			
3142	2024-12-08	Bah Humbug	 				
3145	2024-12-09	Spirit Island	null				
3146	2024-12-10	Spirit Island					
3147	2024-12-11	Cascadia	Onto scenario 3	Won	97		Scenario 2
3148	2024-12-12	Spirit Island	Spirit: Thunderspeaker. Ran out of time (explore cards)	Lost			
3149	2024-12-12	The Crew: Mission Deep Sea					
3150	2024-12-12	Deck the halls					
3151	2024-12-14	Tussie Mussie					
3152	2024-12-15	Bah Humbug					
3153	2024-12-15	Deck the halls					
3154	2024-12-15	For Northwood!					
3155	2024-12-16	For Northwood!	onto next level	won	17		beginner setup
3156	2024-12-17	Deck the halls					
3157	2024-12-17	The Crew: Mission Deep Sea					
3158	2024-12-17	Bah Humbug: the giving spirit					
3159	2024-12-18	Pokemon					
3160	2024-12-18	Pokemon					
3161	2024-12-18	Bah Humbug: the giving spirit					
3162	2024-12-19	For Northwood!	onto summer 2	won	18		Summer 1 (without challenge)
3163	2024-12-19	For Northwood!	onto summer 3	won	16		summer 2 (without challenge)
3164	2024-12-18	Bah Humbug: Ladies Dancing					
3165	2024-12-19	Bah Humbug: Ladies Dancing					
3166	2024-12-19	Bah Humbug					
3167	2024-12-20	Cards: Canasta					
3168	2024-12-20	Bah Humbug					
3169	2024-12-20	Bah Humbug: Ladies Dancing					
3170	2024-12-20	The Crew: Mission Deep Sea					
3171	2024-12-20	SCOUT					
3172	2024-12-25	Bah Humbug: the giving spirit					
3173	2024-12-25	SCOUT					
3174	2024-12-26	Pokemon					
3175	2024-12-27	Bah Humbug					
3176	2024-12-27	Deck the halls					
3177	2024-12-27	Earth					
3178	2024-12-28	Earth	Gaia’s turn				
3179	2024-12-28	7 Wonders					
3180	2024-12-28	Earth		Won	187	142	Beginner
3181	2024-12-29	Imperium: Classics	Romans (me) vs Persian (bot). Bots turn. 				Imperator
3182	2024-12-29	7 Wonders					
3183	2024-12-29	Catan					
3195	2024-12-30	Familiar Tales					
3196	2024-12-30	7 Wonders					
3197	2024-12-31	Imperium: Classics	Bots turn				
3198	2024-12-31	Splendour (Pokémon)					
3199	2024-12-31	Imhotep					
3202	2025-01-01	Imhotep					
3203	2025-01-01	Poo Bingo	great	won			
3204	2025-01-01	Canvas					
3205	2025-01-01	Pokémon: my first battle					
3206	2025-01-01	Imhotep					
3207	2025-01-02	Pokemon					
3208	2025-01-02	Pokémon: my first battle					
3209	2025-01-02	Catan					
3210	2025-01-02	Meadow					
3211	2025-01-03	Earth	Try expert	Won	187	181	Normal
3212	2025-01-03	Pokemon					
3213	2025-01-03	Hogwarts Battle	We won by cheating a lot. Recommend finding the right difficulty. Currently using potions expansion pack 3. Recommend taking away villains, so game shorter. Maybe start with randomly picking an additional high value game at start and remove green dark arts cards. Note gory dark arts cards have been removed. 	Won			
3311	2025-02-02	Splendour (Pokémon)					
3201	2025-01-01	Imperium: Classics	Roman (me) vs Carthaginian (bot). Vikings next. 	Won	68	66	Imperator. Romans (me) vs Carthaginian (bot).
3113	2024-11-24	Imperium: Classics	Bots Turn	Lost	60	73	Imperator. Romans (me) versus Greek (bot).
3214	2025-01-04	Ark Nova	Next: try start 20	Won 	6		Map A, start 15
3215	2025-01-05	Cascadia	Next: scenario 4	Won	93		Scenario 3
3216	2025-01-05	Beez					
3217	2025-01-05	7 Wonders					
3218	2025-01-06	Imperium: Classics	My turn				
3219	2025-01-05	The Bears and the Bees					
3220	2025-01-06	The Bears and the Bees					
3221	2025-01-06	Sleeping Queens					
3222	2025-01-06	Quacks of Quendlinburg					
3224	2025-01-07	Imperium: Classics					
3225	2025-01-08	Imperium: Classics	Bots turn				
3226	2025-01-08	Carcassonne: The City					
3227	2025-01-08	Ticket to Ride					
3229	2025-01-09	Ticket to Ride					
3230	2025-01-09	Onitama					
3231	2025-01-10	Spirit Island					
3232	2025-01-10	Splendour (Pokémon)					
3233	2025-01-11	Spirit Island	Thunderspeaker - thought I was about to win, but then realised made a mistake, but too far along to go back a turn. Have to start again. 	-			
3234	2025-01-11	Familiar Tales					
3235	2025-01-12	Spirit Island	Played thunderspeaker. Next bringer of dreams and nightmares. 	Won			
3236	2025-01-12	Flamecraft					
3237	2025-01-12	Flamecraft					
3238	2025-01-12	Flamecraft					
3239	2025-01-12	Lost Species					
3240	2025-01-12	Lost Species					
3241	2025-01-12	Spirit Island					
3243	2025-01-13	Lost ruins of Arnak					
3244	2025-01-13	Familiar Tales	Campaign complete. Game fully reset. 				
3242	2025-01-13	Spirit Island	Won. Played with bringer of nightmares. Onto scenario or adversary. 				
3245	2025-01-13	Spirit Island	Won. Played with bringer of nightmares. Onto scenario or adversary. 				
3246	2025-01-14	Spirit Island					
3247	2025-01-14	Rat a tat cat					
3248	2025-01-14	Planet					
3249	2025-01-14	Flamecraft					
3250	2025-01-14	Spirit Island					
3251	2025-01-15	Spirit Island	Played river surges in sunlight. Onto next scenario - Blitz using river surges in sunlight again. 	Won			Scenario: Guard the isles heart
3252	2025-01-15	Cascadia					
3253	2025-01-15	Splendour (Pokémon)					
3254	2025-01-15	Lost Species					
3255	2025-01-15	Earth	My turn				
3256	2025-01-16	Earth	Go back to normal mode. 	Lost	160	305	Expert
3257	2025-01-17	Cascadia	Next try Scenario 5.	Won	100		Scenario 4 (All D cards)
3258	2025-01-18	For Northwood!					
3259	2025-01-21	Sushi Go					
3260	2025-01-22	For Northwood!					
3261	2025-01-22	Sushi Go					
3262	2025-01-22	Monopoly Deal					
3263	2025-01-22	Saboteur					
3264	2025-01-22	Cascadia	Onto scenario 6	Won	95		Scenario 5
3265	2025-01-23	For Northwood!	Onto summer 3	Won	17		Scenario summer 2
3266	2025-01-23	For Northwood!	Onto scenario summer 4	Won	16		Scenario summer 3
3267	2025-01-23	7 Wonders Duel					
3268	2025-01-23	Sleeping Queens					
3269	2025-01-23	Imperium: Classics	Bots turn				
3270	2025-01-24	Imperium: Classics	My turn				
3271	2025-01-24	Bohnanza					
3272	2025-01-24	Sleeping Queens 2					
3273	2025-01-24	The Crew: Mission Deep Sea					
3274	2025-01-24	Cards: Wizard					
3275	2025-01-24	Rummikub					
3276	2025-01-25	Imperium: Classics	Try again. Try stopping Vikings from getting any uncivilised (green) and region (yellow) cards. Vikings do well by gaining lots of cards. Main deck empties fast (before Roman’s can build their empire). Region cards need to be bought by Roman’s as Vikings can gain from exile. 	Lost	65	82	Imperator. Romans (me) versus Vikings (bot). 
3277	2025-01-25	Imperium: Classics	Onto Scythians. Won by trying to end game fast before Vikings could gathering lots of cards. 	Won	83	69	Imperator. Roman (me) vs Viking (bot)
3278	2025-01-25	Ticket to Ride					
3279	2025-01-25	Pokémon: my first battle					
3280	2025-01-26	Imperium: Classics	Bots turn				
3281	2025-01-26	Splendour (Pokémon)					
3282	2025-01-26	Imhotep					
3283	2025-01-26	Imperium: Classics	My turn				
3284	2025-01-26	Azul					
3285	2025-01-27	Imperium: Classics	Try again. Bot won with lots of point tokens and population tokens. Bot had lots of region cards. Try prioritising limiting their region cards. 	Lost	60	102	Imperium. Romans (me) vs scythians (bot). 
3286	2025-01-27	Imperium: Classics	Bots turn				
3287	2025-01-27	Imperium: Classics	Bots turn				
3288	2025-01-28	Imperium: Classics	Much better. Focus on taking regions, with particular focus on ones with symbols to block Scythians getting materials. Next focus on getting or exile attack cards and kingdom cards. Let bot collect infinity cards. 	Lost	87	95	Imperator. Roman (me) vs Scythians (bot). 
3289	2025-01-28	Mystic Vale					
3290	2025-01-29	Ares Expedition 					
3291	2025-01-29	Poo Bingo					
3292	2025-01-29	Project L					
3293	2025-01-29	Dominion					
3294	2025-01-29	Onitama					
3295	2025-01-30	Ares Expedition 	Very close. Try again!	Lost	Temp: 8C, Oxy: 11%, 9 ocean flipped, Tr: 37		Novice
3296	2025-01-30	Dominion					
3297	2025-01-30	Dominion					
3298	2025-01-30	Poo Bingo					
3299	2025-01-30	The Crew: Mission Deep Sea					
3300	2025-01-30	Onitama					
3301	2025-01-30	Splendour (Pokémon)					
3302	2025-01-31	Ares Expedition 	Way off. Built a great action machine, but didn’t use the action card to run it until the very end.	Lost	Temp: -10C, Oxy:11%, Ocean: 5, TR 17. 		Novice
3303	2025-01-31	Ares Expedition 					
3304	2025-01-31	Lost Species					
3305	2025-01-31	Stone Age					
3306	2025-02-01	Ares Expedition 	Only just won on the last move. Try novice again. Once consistently easily winning, move onto advanced. 	Won	46		Novice
3307	2025-02-01	Cascadia	Onto scenario 7	Won	90		Scenario 6
3308	2025-02-01	Splendour (Pokémon)					
3309	2025-02-01	Ark Nova					
3310	2025-02-02	Ark Nova	Ooops. Started at 20. Was supposed to start at 10 as won with 15 previously. Next game try starting at 10. 	Won	31		Map A. Start 20 
3228	2025-01-09	Imperium: Classics	Roman (me) vs Viking (bot). Try again. 	Lost	49	82	Imperator. Romans (me) vs Viking (bot).
3312	2025-02-02	Flamecraft					
3313	2025-02-02	Imperium: Classics	Bots turn				
3314	2025-02-03	Imperium: Classics	Won by playing Roman’s very fast, before Scythians could build. Next game try against Macedonians. 	Won	90	70	Imperator. Romans (me) vs Scythians (bot)
3315	2025-02-03	Imperium: Classics	Bots turn				
3316	2025-02-04	Imperium: Classics	Macedonians won by gathered lots of regions. Next game try prioritising buying regions (not exiling). Also try to end game fast. 	Lost	78	90	Imperator. Roman (me) vs Macedonians (bot)
3317	2025-02-05	Imperium: Classics	2nd attempt. Did better at suppressing bot points by grabbing regions, but at the cost of not being able to develop my own civ. 	Lost	55	75	Imperator. Romans (me) vs Macedonians (bot)
3318	2025-02-05	Earth					
3319	2025-02-06	Earth	Too easy. Try expert again. 	Won	225	163	Normal
3320	2025-02-06	Pokemon					
3321	2025-02-06	The Crew: Mission Deep Sea					
3322	2025-02-06	Scribbly Gum					
3323	2025-02-06	Pacific Ocean					
3324	2025-02-06	Pacific Ocean					
3325	2025-02-06	Imperium: Classics	Bots turn				
3326	2025-02-07	Imperium: Classics	Bots turn				
3223	2025-01-06	Imperium: Classics	Romans (me) vs Viking (bot). Lost due to collapse. Try again!	Lost	6	5	Imperator. Romans (me) vs Viking (bot).
3327	2025-02-07	Pokemon					
3328	2025-02-08	Imperium: Classics	Bot had lots of regions gaining lots of points. Block bot from regions, red battles. Best if Macedonians get infinity cards. 	Lost	65	119	Imperator. Romans(me) vs Macedonians (bot)
3329	2025-02-08	Imperium: Classics	Closer. I used innovate to get regions. Was a bit unlucky at end gathering points for myself. Try same tactic again. Grab regions at all cost at start. Try force bot to buy infinity cards. Exile kingdom, and battle cards	Lost	72	92	Imperator. Romans(me) vs macedonians(bot)
3330	2025-02-09	Imperium: Classics	Won by grabbing lots of regions, exiling 5 point cards and red battle cards and force bot to buy infinity cards. Onto celts. 	Won	69	44	Imperator. Romans (me) vs Macedonians (bot). 
3331	2025-02-09	Lost Species					
3332	2025-02-09	Imperium: Classics	Lost due to collapse. Was unlucky with bread and circuses popping up last in the nation deck. 	Lost	7	2	Imperator. Romans (me) vs Celts (bot). 
3333	2025-02-09	Imperium: Classics	Bots turn				
3334	2025-02-10	Imperium: Classics	Won by gaining regions and region scoring cards. Next try legends. 	Won	88	77	Imperator. Romans (me) vs Celts (bot). 
3335	2025-02-10	Dominion					
3336	2025-02-11	Imperium: Classics	Bots turn				
3337	2025-02-12	Imperium: Classics	Bot gave me lots of freedom and game was long, but gained lots of cards and point tokens. Maybe focus on exile cards worth lots of points. Attack cards hurt once civilised. 	Lost	82	101	Imperator. Romans (me) vs Egyptians (bot). 
3338	2025-02-12	Pictures					
3339	2025-02-12	7 Wonders					
3340	2025-02-12	The Crew: Mission Deep Sea					
3341	2025-02-12	Quacks of Quendlinburg					
3342	2025-02-13	Spirit Island					
3343	2025-02-13	Rummikub					
3344	2025-02-13	Spirit Island	Played river surges in sunlight. Onto next scenario - rituals of terror using river surges in sunlight again.	Won			Scenario: Blitz
3345	2025-02-14	Spirit Island	Played river surges in sunlight. Onto next scenario - Dahan insurrection using river surges in sunlight again.	Won			Scenario: rituals of terror. 
3346	2025-02-15	Wingspan		Lost	76	80	Normal ( x 4 )
3347	2025-02-16	Ares Expedition 					
3348	2025-02-16	Ares Expedition 					
3349	2025-02-16	Catan					
3350	2025-02-17	Ares Expedition 	Won very easily by having lots of money. Try advanced mode (only moving oxygen or temp 1 step each round). 	Won	69		Novice
3351	2025-02-17	Imperium: Classics	My turn				
3352	2025-02-18	Imperium: Classics	Bot gained lots of cards. Not enough time for me to build engine. Try blocking red battle cards, attack cards, water region cards, high point cards. 	Lost	62	83	Imperator. Romans (me) vs Egyptians (bot)
3353	2025-02-18	Imperium: Classics	Bot one lots of point tokens (36) from converting population tokens. Bot plowed through nation deck, so faster game. Try again. Exile attack, battle. Focus on buying regions quickly. 	Lost	86	99	Imperator. Romans(me) vs Egyptians (bot)
3354	2025-02-19	Imperium: Classics	My turn				
3355	2025-02-19	Cluedo					
3356	2025-02-19	Imperium: Classics	Bots turn				
3370	2025-02-27	Imperium: Classics	Lost due to collapse. In solo, always lose if there is a collapse. 	Lost	4	5	Imperator. Romans (me) vs Minoans (bot)
3357	2025-02-20	Imperium: Classics	Built a great deck and finished perfect timing before bot got too powerful. Mauryans next. 	Won	103	95	Imperator. Romans (me) vs Egyptians (bot). 
3358	2025-02-20	Sushi Go					
3359	2025-02-20	The Bears and the Bees					
3360	2025-02-20	Earth	My turn				
3361	2025-02-21	Earth	Nice and close. Try again. 	Lost	168	185	Expert
3362	2025-02-21	Pokemon					
3363	2025-02-22	Imperium: Classics	Bots turn				
3364	2025-02-22	Imperium: Classics	Wow. Got lucky!	Won	76	74	Imperator. Romans (me) vs Mauryans (bot)
3365	2025-02-23	Imperium: Classics	Bots turn				
3366	2025-02-24	Imperium: Classics	My turn				
3367	2025-02-25	Imperium: Classics	There were a couple of point cards I missed out on. Exile attacks and plain civ and plain unciv and kingdom. 	Lost	67	77	Imperator. Romans (me) vs Minoans (bot)
3368	2025-02-25	Imperium: Classics	Bots turn				
3369	2025-02-27	Imperium: Classics	Close. Minoans had lots of cards. Exile valuable cards. 	Lost	88	95	Imperator. Romans (me) vs Minoans (bot). 
3371	2025-02-27	Imperium: Classics	Soooooo close	Lost	70	71	Imperator. Romans(me) vs Minoans (bot). 
3372	2025-02-27	Imperium: Classics	Bots turn				
3373	2025-02-28	Imperium: Classics		Won	82	78	Imperator. Romans (me) vs Minoans (bot). 
3374	2025-02-28	Lost Species					
3375	2025-03-01	Ares Expedition 	Won very easily with one round still to go. Try expert mode ( no bonuses given). 	Won			Advanced
3376	2025-03-02	Spirit Island	Played as river surges in sunlight. Try again. 	Lost			Scenario: dahan insurrection
3377	2025-03-04	Imperium: Classics	Bots turn				
3378	2025-03-05	Imperium: Classics	My turn				
3379	2025-03-05	Imperium: Classics	Bots turn				
3380	2025-03-06	Imperium: Classics	Olmecs let Roman’s do as they please. 	Won	112	86	Imperator. Romans (me) vs Olmecs (bot). 
3381	2025-03-05	Quacks of Quendlinburg					
3382	2025-03-08	Meadow					
3383	2025-03-09	Ticket to Ride					
3384	2025-03-10	Wingspan					
3385	2025-03-10	Wingspan					
3386	2025-03-13	Imperium: Classics	My turn				
3387	2025-03-13	Pokemon					
3388	2025-03-13	Imperium: Classics		Lost	Collapse		Imperator. Roman (me) vs Qin (bot)
3389	2025-03-13	Imperium: Classics	My turn				
3390	2025-03-14	Imperium: Classics	My turn				
3391	2025-03-14	Splendour (Pokémon)					
3392	2025-03-15	Imperium: Classics	Try block attack and battle. Then infinity. Allow normal civilised and uncivilised cards. 	Lost	43	52	Imperator. Romans (me) vs Qin (bot)
3393	2025-03-15	Splendour (Pokémon)					
3394	2025-03-15	Pokemon					
3395	2025-03-15	Dominion					
3396	2025-03-15	Rat a tat cat					
3397	2025-03-15	Taco cat goat ...					
3398	2025-03-15	Rat a tat cat					
3399	2025-03-15	Ares Expedition 					
3400	2025-03-16	Ares Expedition 					
3401	2025-03-16	Imhotep					
3402	2025-03-16	Rat a tat cat					
3403	2025-03-16	Ares Expedition 					
3404	2025-03-17	Ares Expedition 	Remember bot starts 1TR	Lost	-10 C, 6 %, 9 ocean flipped		Expert
3405	2025-03-18	Ares Expedition 	Try advanced. Moving one per round. 	Lost	-2 C, 5 %, 3 ocean flipped. 		Expert
3406	2025-03-18	Ares Expedition 					
3407	2025-03-19	Ares Expedition 	Won on last turn	Won			Expert
3408	2025-03-19	Flamme Rouge					
3409	2025-03-20	Project L					
3410	2025-03-20	Ares Expedition 					
3411	2025-03-21	Ares Expedition 		Lost	8 C, 9%, 9 ocean tiles		Expert
3412	2025-03-21	Project L					
3413	2025-03-22	Earth	My turn				
3414	2025-03-22	Flamme Rouge					
3415	2025-03-22	Earth	Bots turn				
3416	2025-03-23	Earth	Try again. 	Lost	157	233	Expert
3417	2025-03-23	Earth	Try again	Lost	187	198	Expert
3418	2025-03-23	Flamme Rouge					
3419	2025-03-23	Calico	Next try challenge 3				
3420	2025-03-23	Cascadia	Soooo close. Try again	Lost	89		Scenario 7
3421	2025-03-23	Cascadia	Onto scenario 8	Won	94, 27 hawks	90, 20 hawks	Scenario 7
3422	2025-03-23	Splendour (Pokémon)					
3423	2025-03-23	Pokemon					
3424	2025-03-23	Spirit Island	All scenarios complete	Won			Scenario: Dahan insurrection
3425	2025-03-24	Spirit Island					
3426	2025-03-24	Pokémon: my first battle					
3427	2025-03-24	Spirit Island					
3428	2025-03-25	Spirit Island	Try level 2. Although I did do a bit of spirit land adjusting.  Try without. 	Won			The Kingdom of Brandenburg-Prussia. Level 1
3429	2025-03-26	Imperium: Classics	Bots turn				
3430	2025-03-25	Monopoly Deal					
3431	2025-03-26	Imperium: Classics	Bots turn				
3432	2025-03-27	Imperium: Classics	Sooo close. Try again. Block attacks, battle then infinity. Allow normal civilised and uncivilised. 	Lost	79	82	Imperator. Romans(me) vs Qin (bot). 
3433	2025-03-27	Imperium: Classics	My turn				
3434	2025-03-28	Imperium: Classics	Bot won by gaining lots of cards. Think how to reduce cards gained by bot. 	Lost	58	77	Imperator. Romans (me) vs Qin (bot). 
3435	2025-03-28	Imperium: Classics	Bots turn				
3436	2025-03-29	Imperium: Classics		Won	92	86	Imperator. Romans (me) vs Qin (bot)
3437	2025-03-29	7 Wonders					
3438	2025-03-29	Pokemon					
3439	2025-03-30	Ark Nova	Try a harder level. Maybe start at 5 or try different map. 	Won	10	0	Map A. Start 10. 
3440	2025-03-30	Karuba					
3441	2025-03-30	Splendour (Pokémon)					
3442	2025-03-30	Mystic Vale					
3443	2025-03-30	Ares Expedition 					
3444	2025-03-31	Ares Expedition 	Soooooo close. Try again. 	Lost	8 C, 13 %, 9 ocean Tiles	8 C, 14 %, 9 ocean tiles	Expert
3445	2025-03-31	Ares Expedition 					
3446	2025-03-31	Ares Expedition 	Try again	Lost	-8 C, 6 %, 9 tiles	8 C, 14 %, 9 tiles	Expert
3447	2025-04-01	Ares Expedition 	Sooooo fun! Try again. 	Lost	-6 C, 14 %, 7 tiles	8 C, 14%, 9 tiles	Expert
3448	2025-03-31	Marvel United					
3449	2025-04-02	Ares Expedition 					
3450	2025-04-03	Ares Expedition 	Try again!	Lost	8 C, 11 %, 9 tiles	8 C, 14 %, 9 tiles	Expert
3451	2025-04-03	Ark Nova					
3452	2025-04-04	Ark Nova	Try map 0, start 15	Won	10	0	Map 0, start 20
3453	2025-04-05	Imperium: Classics	Got smashed! Try block attack and infinity and civilised. Allow battle and tributary. Buy cards cause bot to recall region	Lost	37	75	Imperator. Romans (me) vs Atlanteans (bot). 
3454	2025-04-05	Imperium: Classics	Soo tough. Block attack, infinity and civilised. Allow battle and kingdom. Buy cards to force bot to abandon regions. 	Lost	62	95	Imperator. Romans (me) vs Atlanteans (bot)
3455	2025-04-07	Century: Spice Road	Bots turn				
3456	2025-04-07	Everdell: My Lil'					
3457	2025-04-07	Century: Spice Road	Try again	Lost	78	93	Standard
3458	2025-04-08	Draftosaurus					
3459	2025-04-05	Canvas					
3460	2025-04-05	Pokemon					
3461	2025-04-05	Tussie Mussie					
3462	2025-04-05	7 Wonders					
3463	2025-04-05	Monopoly Deal					
3464	2025-04-05	Pacific Ocean					
3465	2025-04-06	Splendour (Pokémon)					
3466	2025-04-06	Cascadia					
3467	2025-04-06	Unstable Unicorns: Travel					
3468	2025-04-08	Century: Spice Road					
3469	2025-04-09	Century: Spice Road					
3470	2025-04-09	Forbidden Desert					
3471	2025-04-09	Forbidden Island					
3472	2025-04-10	Century: Spice Road	Sooo close. Try again. 	Lost	79	83	Standard
3473	2025-04-10	Century: Spice Road	Try eastern	Won	80	61	Normal
3474	2025-04-11	Mystic Vale					
3475	2025-04-11	Flamme Rouge					
3476	2025-04-12	Splendour (Pokémon)					
3477	2025-04-14	Century: Eastern	My turn				
3478	2025-04-14	Meadow					
3479	2025-04-14	Tiny Towns					
3480	2025-04-14	Century: Eastern	My turn				
3481	2025-04-15	Bohnanza					
3482	2025-04-15	The Crew: Mission Deep Sea					
3483	2025-04-15	Dragomino					
3484	2025-04-17	Century: Eastern	Try new world	Won	73	43	Standard
3485	2025-04-20	Ticket to Ride					
3486	2025-04-18	Pokemon					
3487	2025-04-19	Pokemon					
3488	2025-04-19	Ark nova minima					
3489	2025-04-19	Cascadia		Lost	85	90	Scenario 8
3490	2025-04-19	Ares Expedition 		Lost	-2 C, 9 %, 5 tiles		Expert  
3491	2025-04-20	Mystic Vale					
3492	2025-04-20	The Bears and the Bees					
3493	2025-04-20	The Bears and the Bees					
3494	2025-04-20	Ark nova minima					
3495	2025-04-21	Ares Expedition 		Lost	-18 C, 6 %, 7 tiles	8 C, 14%, 9 tiles	Expert
3496	2025-04-21	Pokemon					
3497	2025-04-21	Pokemon					
3498	2025-04-22	Sleeping Gods	1 action left, loc 186, ship 5				
3499	2025-04-22	Dinosaur Tea Party					
3500	2025-04-23	Sleeping Gods					
3501	2025-04-23	Scribbly Gum					
3502	2025-04-24	Sleeping Gods	New turn				
3503	2025-04-24	Scribbly Gum					
3504	2025-04-24	Sleeping Gods	Need to spend XP, then end of first action				
3505	2025-04-25	Sleeping Gods	Start turn, ship near 68, meeple on bridge. 				
3506	2025-04-25	Scribbly Gum					
3507	2025-04-25	Pass the party food					
3508	2025-04-23	Flamme Rouge					
3509	2025-04-26	Sleeping Gods	New turn. Explore 60 again. 				
3510	2025-04-27	Sleeping Gods	New turn. Go to 107, then 132. 				
3511	2025-04-27	Scribbly Gum					
3512	2025-04-28	Sleeping Gods	About to explore 107. Have done event and gained command for exploring  				
3513	2025-04-28	Sleeping Gods	Start new turn. Travel to 69 and explore. Ship currently in glance. Ship token on 5. 				
3514	2025-04-29	Sleeping Gods	New turn, ship token - cargo bay, ship at 114				
3515	2025-04-30	Sleeping Gods	Start new turn. Ship on 120, ship token on bridge				
3516	2025-05-01	Sleeping Gods	New turn. Ship 84, token on cargo bay. 				
3517	2025-05-01	Sleeping Queens 2					
3518	2025-05-01	Sleeping Gods	New turn. Ship on 146. Token on Deck. 				
3519	2025-05-02	Sleeping Gods					
3520	2025-05-03	Sleeping Gods	New turn. Ship loc 158. Ship token cargo bay. 				
3521	2025-05-03	Splendour (Pokémon)					
3523	2025-05-04	Wingspan					
3522	2025-05-04	Sleeping Gods	Completed campaign. One defeat. 4 totems. Ending 1. 				
3524	2025-05-04	Sleeping Gods	Completed campaign. One defeat. 4 totems. Ending 1. 				
3525	2025-05-05	Imperium: Classics	Lost due to Collapse	Lost	3 unrest	5 unrest	Imperator. Romans (me) vs Atlanteans (bot). 
3526	2025-05-06	Imperium: Classics	Getting closer. Try again. Block attack, civilised, infinity. Allow battle and tributary. Don’t forget myths and legends fame purchases. 	Lost	82	92	Imperator. Romans (me) vs Atlanteans (bot)
3527	2025-05-08	Imperium: Classics	My turn				
3528	2025-05-09	Imperium: Classics	My turn				
3529	2025-05-09	Imperium: Classics	Smashed! Unlucky. Try again. 	Lost	36	101	Imperator. Romans (me) vs Atlanteans (bot)
3530	2025-05-09	Imperium: Classics	Bots turn				
3531	2025-05-10	Imperium: Classics	Need new tactic. Force bot get battle or kingdom. Not infinity, civ, attack. 	Lost	58	114	Imperator. Romans (me) vs Atlanteans (bot)
3532	2025-05-10	Planet					
3533	2025-05-10	Imperium: Classics	Bots turn				
3534	2025-05-10	7 Wonders					
3535	2025-05-10	Imperium: Classics	Closer. 	Lost	62	87	Imperator. Romans (me) vs Atlanteans (bot)
3536	2025-05-11	Imperium: Classics	My turn				
3537	2025-05-11	Rummikub					
3538	2025-05-12	Imperium: Classics	Bots turn				
3539	2025-05-12	Lost Species					
3540	2025-05-13	Imperium: Classics	Tried let bot have attacks. Bot still high points. Try something else. 	Lost	41	88	Imperator. Romans (me) vs Atlanteans (bot)
3541	2025-05-13	Lost Species					
3542	2025-05-14	Imperium: Classics	Better. Weakened bot deck. Gave lots of attack. Tried to reduce high point cards and infinity cards. Bought attack cards. Tried to ensure I had lots of point tokens. Try again, but need to work out how to score more. 	Lost	48	74	Imperator. Romans (me) vs Atlanteans (bot)
3543	2025-05-15	Pokemon					
3544	2025-05-15	Splendour (Pokémon)					
3545	2025-05-15	Imperium: Classics	Bots turn				
3546	2025-05-16	Imperium: Classics	I allowed attacks, civ and trib and exiled infinity. Worked, but I simultaneously need to get high points for myself. Maybe accept defeat for this one and move on?	Lost	43	77	Imperator. Romans (me) vs Atlanteans (bot)
3547	2025-05-17	Sleeping Gods	1 action left, ship on 2 , token on cargo bay				
3548	2025-05-18	Sleeping Gods	Start new turn, ship on 120, token on cargo bay. 				
3549	2025-05-18	Pokemon					
3550	2025-05-18	Pictures					
3551	2025-05-18	Sleeping Gods	Start combat 43,44,45				
3552	2025-05-20	Sleeping Gods	New turn. At Lynn’s grove. Token in cargo bay. 				
3553	2025-05-21	Horizons of Spirit Island					
3554	2025-05-22	Pokemon					
3555	2025-05-23	Pokemon					
3556	2025-05-24	Sleeping Gods	About to start first action. Ship on 155. Token on bridge. 				
3557	2025-05-26	Sleeping Gods	Start new turn ship on 181 token on quarters				
3558	2025-05-26	Splendour (Pokémon)					
3559	2025-05-27	Sleeping Gods	Just finished first event deck. About to start 1. Ship on 151. Token on bridge. 				
3560	2025-05-28	Sleeping Gods	Start new turn. Ship on 213. Token on bridge				
3561	2025-05-30	Mancala					
3562	2025-05-31	Sleeping Gods	Ship on 84. Token on bridge. Start new turn. 				
3563	2025-06-02	Poo Bingo					
3564	2025-06-02	Memory					
3565	2025-06-02	Beez					
3566	2025-06-09	Unstable Unicorns					
3567	2025-06-11	Horizons of Spirit Island					
3568	2025-06-09	Dorfromantik					
3569	2025-06-12	Dorfromantik					
3570	2025-06-15	Everdell					
3571	2025-06-15	Azul					
3572	2025-06-15	Everdell					
3573	2025-06-16	Everdell		Won	45	37	Year 1
3574	2025-06-18	Dorfromantik					
3575	2025-06-19	Dorfromantik					
3576	2025-06-20	Dorfromantik					
3577	2025-06-22	Dorfromantik					
3578	2025-06-21	Dorfromantik					
3579	2025-06-22	Dorfromantik					
3580	2025-06-23	Dorfromantik					
3581	2025-06-23	Imhotep					
3582	2025-06-26	Dorfromantik					
3583	2025-06-25	Bah Humbug					
3584	2025-06-26	Pokemon					
3585	2025-06-26	Dorfromantik					
3586	2025-06-27	Monopoly Deal					
3587	2025-06-29	Dorfromantik					
3588	2025-07-01	Ares Expedition 		Lost	-2 C, 12%, 7 O2,  35 MC	8 C, 14%, 9 O2	Expert
3589	2025-07-01	Rummikub					
3590	2025-07-01	Pokemon					
3591	2025-07-02	Dorfromantik					
3592	2025-07-03	Splendour (Pokémon)					
3593	2025-07-03	Dorfromantik					
3594	2025-07-07	The Robber Hotzenplotz					
3595	2025-07-10	Pokemon					
3596	2025-07-17	Quacks of Quendlinburg					
3597	2025-07-20	Imperium: Classics	Bots turn				
3598	2025-07-20	Lost ruins of Arnak					
3599	2025-07-21	Imperium: Classics	Bots turn 				
3600	2025-07-24	Imperium: Classics	Bots turn				
3601	2025-07-25	Imperium: Classics	Might be time to move on. 	Lost. Romans (me) vs Atlanteans (bot)	53	98	Imperator 
3602	2025-07-26	Catan	Successful even game. Knight or 7 gets to pick one resource. I supported anyone struggling or even game them a free resource. 				
3603	2025-07-26	Cascadia	Onto scenario 9	Won	95, 6 pine cones	90, 5 pine cones	Scenario 8
3604	2025-07-26	Cascadia					
3605	2025-07-26	Dorfromantik					
3606	2025-07-28	Dorfromantik					
3607	2025-07-31	Dorfromantik					
3608	2025-08-06	Monopoly Deal					
3609	2025-08-09	Azul					
3610	2025-08-10	The Crew: Mission Deep Sea					
3611	2025-08-18	Hogwarts Battle					
3612	2025-08-18	Hogwarts Battle					
3613	2025-08-18	Hogwarts Battle					
3614	2025-08-23	Mystic Vale					
3615	2025-08-24	Hogwarts Battle					
3616	2025-08-29	Mystic Vale					
3617	2025-08-30	Concordia					
3618	2025-08-31	Pokemon					
3619	2025-08-31	Pokemon					
3620	2025-09-07	Concordia	Luci’s turn 				
3621	2025-09-10	Forbidden Desert					
3622	2025-09-10	Forbidden Island					
3623	2025-09-11	Hogwarts Battle	Up to game 7				
3624	2025-09-11	Pokemon					
3625	2025-09-13	Hogwarts Battle					
3626	2025-09-13	Hogwarts Battle					
3627	2025-09-13	Splendour (Pokémon)					
3628	2025-09-14	The Crew: Mission Deep Sea					
3629	2025-09-14	Pokémon: my first battle					
3630	2025-09-19	Targi					
3631	2025-09-21	Splendour (Pokémon)					
3632	2025-09-21	Monopoly Deal					
3633	2025-09-21	7 Wonders					
3634	2025-09-23	Hogwarts Battle					
3635	2025-09-23	Hogwarts Battle					
3636	2025-09-23	Hogwarts Battle					
3637	2025-09-24	Pokémon: my first battle					
3638	2025-09-28	Uno - Harry Potter					
3639	2025-09-29	Uno - Harry Potter					
3640	2025-09-30	Uno - Harry Potter					
3641	2025-10-01	Uno - Harry Potter					
3642	2025-10-01	Star Wars Unlimited					
3643	2025-10-02	Star Wars Unlimited					
3644	2025-10-03	Star Wars Unlimited					
3645	2025-10-05	Star Wars Unlimited					
3646	2025-10-06	Lorcana					
3647	2025-10-05	Lorcana					
3648	2025-10-03	Uno - Harry Potter					
3649	2025-10-06	Lorcana					
3650	2025-10-06	Lorcana					
3651	2025-10-06	Bohnanza					
3652	2025-10-07	Everdell	Nightweave turn				
3653	2025-10-11	Sushi Go					
3654	2025-10-11	Lorcana					
3655	2025-10-11	7 Wonders Duel					
3656	2025-10-12	Draftosaurus					
3657	2025-10-12	Azul					
3658	2025-10-14	Imperium: Classics	My turn				
3659	2025-10-14	Imperium: Classics	Lost via a collapse	Lost			Imperator. Romans (Me) vs Arthurians (bot)
3660	2025-10-14	Imperium: Classics	Bots turn				
3661	2025-10-15	Imperium: Classics	Bots turn				
3662	2025-10-15	Imperium: Classics	Bots turn				
3663	2025-10-17	Imperium: Classics		Lost	46	65	Imperator. Roman’s (me) vs Arthurians (bot)
3664	2025-10-18	Lorcana					
3665	2025-10-18	Imperium: Classics	My turn				
3666	2025-10-19	Lorcana					
3667	2025-10-19	Imhotep					
3668	2025-10-23	Imperium: Classics		Lost	54	65	Imperator. Roman’s (me) vs Arthurians (bot). 
3669	2025-10-23	Everdell					
3670	2025-10-24	Imperium: Classics	Bots turn				
3671	2025-10-25	Lorcana					
3672	2025-10-25	7 Wonders					
3673	2025-10-25	Hanamikoji					
3674	2025-10-26	Imperium: Classics		Won	83	64	Imperator. Romans (me) vs Arthurians (bot)
3675	2025-10-27	Lorcana					
3676	2025-10-27	Splendour (Pokémon)					
3677	2025-10-27	Splendour (Pokémon)					
3678	2025-10-30	Magic Maze					
3679	2025-11-01	Pokemon					
3680	2025-11-01	Quacks of Quendlinburg					
3681	2025-11-01	Imperium: Classics	My turn 				
3682	2025-11-02	Lorcana					
3683	2025-11-02	Valley of the Vikings					
3684	2025-11-02	Imperium: Classics	My turn				
3685	2025-11-03	Imperium: Classics	My turn				
3686	2025-11-05	Imperium: Classics	My turn				
3687	2025-11-05	Geminion					
3688	2025-11-06	Imperium: Classics	Bots turn				
3689	2025-11-06	Imperium: Classics	Bots turn				
3690	2025-11-07	Imperium: Classics		Lost. Romans(me) vs Abbasids (bot)	111 	113	Imperator 
3691	2025-11-09	Imperium: Classics	My turn				
3692	2025-11-09	Lorcana					
3693	2025-11-09	Bohnanza					
3694	2025-11-09	Cascadia					
3695	2025-11-09	Coconuts					
3696	2025-11-09	Imperium: Classics	Bots turn				
3697	2025-11-10	Imperium: Classics	My turn				
3698	2025-11-13	Imperium: Classics		Lost 	103	123	Imperator. Romans (me) vs Abbasids (bot)
3699	2025-11-13	Imperium: Classics	Lost via Collapse. Only had 1 turn! 	Lost			Imperator. Romans (me) vs Abbasids (bot) 
3700	2025-11-13	Imperium: Classics	Bots turn				
3701	2025-11-14	Scribbly Gum					
3702	2025-11-14	Carcassonne: The City					
3703	2025-11-14	Imperium: Classics	Bots turn				
3704	2025-11-14	Imperium: Classics		Lost	116	141	Imperator. Romans (me) vs Abbasids (bot)
3705	2025-11-15	Imperium: Classics	My turn				
3706	2025-11-15	Imperium: Classics	Bots turn				
3707	2025-11-15	Imperium: Classics	My turn				
3708	2025-11-15	Imperium: Classics		Won	139	132	Imperator. Romans (me) vs Abbasids (bot)
3709	2025-11-16	Splendour (Pokémon)					
3710	2025-11-16	Cascadia					
3711	2025-11-16	Pokemon					
3712	2025-11-16	Lorcana					
3713	2025-11-22	Flamecraft					
3714	2025-11-21	Flamecraft					
3715	2025-11-20	Flamecraft					
3716	2025-11-22	Sleeping Queens 2					
3717	2025-11-23	Pokemon					
3718	2025-11-23	Lorcana					
3719	2025-11-24	Sleeping Queens					
3720	2025-11-29	Mystic Vale					
3721	2025-11-29	Spirit Island		Won			River surges in sunlight with events
3722	2025-11-30	Spirit Island					
3723	2025-11-30	Santa's workshop					
3724	2025-11-30	Bah Humbug					
3725	2025-11-30	Bah Humbug: Ladies Dancing					
3726	2025-12-04	Pokemon					
3727	2025-12-04	Spirit Island					
3728	2025-12-06	Pokemon					
3729	2025-12-06	Bah Humbug: Ladies Dancing					
3730	2025-12-06	Pokemon					
3731	2025-12-06	Spirit Island		Won			River surges in sunlight with events. 
3732	2025-12-07	Bah Humbug: Deck Build the Halls					
3733	2025-12-14	Castle Panic					
3734	2025-12-14	Top Trumps: Toy Story					
3735	2025-12-19	Star Wars Unlimited					
3736	2025-12-23	Pokemon					
3737	2025-12-23	Castle Panic					
3738	2025-12-23	The Crew: Mission Deep Sea					
3739	2025-12-21	The Lord of the Rings: The Fellowship of the Ring					
3740	2025-12-22	The Lord of the Rings: The Fellowship of the Ring					
3741	2025-12-27	The Lord of the Rings: The Fellowship of the Ring					
3742	2025-12-27	The Lord of the Rings: The Fellowship of the Ring		won			Chapter 3
3743	2025-12-27	Cards: Canasta					
3744	2025-12-27	Star Wars Unlimited					
3745	2025-12-28	The Lord of the Rings: The Fellowship of the Ring	completed chapter 4				
3746	2025-12-30	Lorcana					
3747	2026-01-01	Lorcana		Won			Easy
3748	2026-01-02	Lorcana	Try normal	Won			Easy
3749	2026-01-04	Lorcana		Lost			Normal
3750	2026-01-05	Lorcana					
3751	2026-01-05	Draftosaurus					
3752	2026-01-06	Kingdomino					
3753	2026-01-06	Imhotep					
3754	2026-01-06	Pokémon: my first battle					
3755	2026-01-07	Poo Bingo					
3756	2026-01-09	Karuba					
3757	2026-01-10	Forbidden Desert					
3758	2026-01-09	Pictures					
3759	2026-01-11	Dragomino					
3760	2026-01-11	Flamecraft					
3761	2026-01-11	Lorcana					
3762	2026-01-11	Dragomino					
3763	2026-01-12	Lorcana					
3764	2026-01-13	Lorcana					
3765	2026-01-14	Lorcana					
3766	2026-01-14	Lorcana					
3767	2026-01-15	Hogwarts Battle					
3768	2026-01-15	Lorcana					
3769	2026-01-15	Lorcana					
3770	2026-01-16	Lorcana					
3771	2026-01-16	Lorcana					
3772	2026-01-16	Lorcana					
3773	2026-01-17	Scribbly Gum					
3774	2026-01-17	Lorcana					
3775	2026-01-17	Flamme Rouge					
3776	2026-01-18	Lorcana					
3777	2026-01-19	Lorcana					
3778	2026-01-19	Lorcana					
3779	2026-01-20	Lorcana					
3780	2026-01-20	Lorcana					
3781	2026-01-21	Lorcana					
3782	2026-01-21	Lorcana					
3783	2026-01-22	Cascadia					
3784	2026-01-23	Lorcana					
3785	2026-01-28	Lorcana					
3786	2026-01-28	Pokemon					
3787	2026-01-31	Targi					
3788	2026-02-01	Hogwarts Battle					
3789	2026-02-08	Lorcana					
3790	2026-02-15	Pokemon					
3791	2026-02-15	Imperium: Classics	My turn				
3792	2026-02-16	Imperium: Classics	My turn				
3793	2026-02-16	Imperium: Classics	My turn				
3794	2026-02-17	Imperium: Classics	Yay!	Won	107	103	Romans (me) vs Aksumites (bot)
3795	2026-02-23	Imperium: Classics	Bots turn				
3796	2026-02-23	Imperium: Classics	Bots turn				
3797	2026-02-24	Imperium: Classics	Imperator 	Lost 	79	103	Romans (me) vs Guptas (bot)
3798	2026-02-28	Lorcana					
3799	2026-03-01	Hogwarts Battle					
3800	2026-03-01	Hogwarts Battle					
3801	2026-03-08	Scribbly Gum					
3802	2026-03-08	The Bears and the Bees					
3803	2026-03-12	Saboteur					
3804	2026-03-14	Lorcana					
3805	2026-03-15	The Bears and the Bees					
3806	2026-03-22	Pass the party food					
3807	2026-03-29	Dragomino					
3808	2026-03-29	Kingdomino					
3809	2026-03-29	Imperium: Classics	Bots turn				
3810	2026-03-30	Imperium: Classics	Bots turn				
3811	2026-03-31	Imperium: Classics	Bots turn				
3813	2026-04-04	Splendour (Pokémon)					
3814	2026-04-05	Lorcana					
3815	2026-04-05	Rummikub					
3816	2026-04-05	Kung Fu Panda	Completed training missions				
3817	2026-04-06	Kung Fu Panda					
3818	2026-04-06	Kung Fu Panda					
3820	2026-04-07	Splendour (Pokémon)					
3812	2026-04-03	Imperium: Classics		Won. 	149	115	Imperator. Romans (me) vs Guptas (bot)
3821	2026-04-07	Kung Fu Panda					
3822	2026-04-09	Kingdomino					
3823	2026-04-09	Century: Spice Road					
3824	2026-04-10	The Bears and the Bees					
3825	2026-04-10	Kung Fu Panda					
3826	2026-04-11	Splendour (Pokémon)					
3827	2026-04-12	Monopoly Deal					
3828	2026-04-11	Splendour (Pokémon)					
3829	2026-04-11	Kung Fu Panda					
3830	2026-04-11	The Bears and the Bees					
3831	2026-04-14	Dinosaur Tea Party					
3832	2026-04-15	Imperium: Classics	Bot Infinity and red hammer cards powerful in this game. 	Lost	67	91	Imperator. Romans (me) vs Magyars (bot)
3833	2026-04-18	Star Wars Unlimited	Leia vs Darth Vader 				
3834	2026-04-19	Star Wars Unlimited					
3835	2026-04-19	Star Wars Unlimited					
3836	2026-04-20	Star Wars Unlimited					
3837	2026-04-23	Star Wars Unlimited					
3838	2026-04-25	Star Wars Unlimited					
3839	2026-04-25	Star Wars Unlimited					
3840	2026-04-26	Kung Fu Panda		Won			Mission 3.1
3841	2026-04-27	Star Wars Unlimited					
3842	2026-04-29	Fairytale in my pocket					
3843	2026-04-30	Star Wars Unlimited					
3844	2026-05-02	The Lord of the Rings: The Fellowship of the Ring	Move onto chap 3	Won			2
3845	2026-05-02	Star Wars Unlimited					
3846	2026-05-02	The Lord of the Rings: The Fellowship of the Ring	Onto chap 4	Won			Chapter 3
3847	2026-05-04	Star Wars Unlimited					
3848	2026-05-05	Star Wars Unlimited					
3849	2026-05-06	Star Wars Unlimited					
3850	2026-05-06	Star Wars Unlimited					
3851	2026-05-07	Star Wars Unlimited					
3852	2026-05-09	Star Wars Unlimited					
3853	2026-05-09	The Lord of the Rings: The Fellowship of the Ring	Up to chapter 6				
3854	2026-05-10	The Lord of the Rings: The Fellowship of the Ring	Onto chap 7	Won			Chapter 6
3855	2026-05-10	Hotzenplotz					
3856	2026-05-10	Sushi Go					
3857	2026-05-10	The Lord of the Rings: The Fellowship of the Ring					
3858	2026-05-13	Geminion					
3859	2026-05-14	Bohnanza					
3860	2026-05-14	Valley of the Vikings					
3861	2026-05-16	Star Wars Unlimited					
3862	2026-05-16	7 Wonders					
3863	2026-05-17	Calico					
3864	2026-05-17	Uno - Harry Potter					
3865	2026-05-17	Uno - Harry Potter					
3866	2026-05-17	Magic Maze					
3867	2026-05-17	Imhotep					
3868	2026-05-18	Quacks of Quendlinburg					
3869	2026-05-19	Taco cat goat ...					
3870	2026-05-19	Star Wars Unlimited					
3871	2026-05-20	Forbidden Desert					
3872	2026-05-21	Karuba					
3873	2026-05-22	Kung Fu Panda					
3874	2026-05-23	Uno - Harry Potter					
3875	2026-05-24	Cascadia					
3876	2026-05-24	Uno - Harry Potter					
3877	2026-05-24	The Bears and the Bees					
3878	2026-05-25	Star Wars Unlimited					
3879	2026-05-26	Star Wars Unlimited					
3880	2026-05-26	Imperium: Classics	My turn				
3881	2026-05-28	Imperium: Classics	Bots turn				
3882	2026-05-28	Imperium: Classics	Bots turn				
3883	2026-05-29	Pass the party food					
3884	2026-05-29	Pass the party food					
3885	2026-05-30	Star Wars Unlimited					
3886	2026-05-31	Imperium: Classics		Lost.	82	116	Imperator. Romans (me) vs Magyars (bot)
3887	2026-05-30	Kingdomino					
3888	2026-05-31	Canvas					
3889	2026-05-31	Dragomino					
3890	2026-05-31	Kung Fu Panda					
3891	2026-06-01	Rummikub					
3892	2026-06-01	Santorini					
3893	2026-06-02	Ark Nova					
3894	2026-06-02	Ark Nova	Try map 0. Start 10. 	Won			Map 0, start 15
3895	2026-06-02	Dragonstark					
3896	2026-06-02	Scribbly Gum					
\.


--
-- Data for Name: sleeping_gods; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sleeping_gods (location, part, required_keyword, gained_keyword, visited, notes, combat, combat_level, gained, lost, req_coins, req_meat, req_veg, req_grain, req_artifacts, gain_coins, gain_meat, gain_veg, gain_grain, gain_artifacts, req_wood, gain_wood, gain_xp, gain_ship_damage, gain_ship_repair, gain_crew_damage, gain_crew_health, gain_low_morale, gain_fright, gain_venom, gain_weakness, gain_madness, remove_low_morale, remove_fright, remove_venom, remove_weakness, remove_madness, totem, challenge, challenge_level, gain_totem, gain_adventure, defeats, id) FROM stdin;
1	2 B			f		f	0	2 XP	Remove 1 morale	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	1
1	2 B 4 C			f		t	17			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	2
174		AUCTION		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	3
174		FOAM		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	4
18	A		HUNTED	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	5
2		IRON		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	6
186		SHRINE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	7
174		PASSWORD		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	8
172	2	RUSH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	232
34		Cottage		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	10
216		MAIL		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	11
216	C			f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	12
30		ROTTEN		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	13
30	A			f	Pass: Gain meat	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	14
7		FREIGHTER		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	15
7	A			f	Singing shrimp. Gained meat. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	16
130		UNLEASH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	17
130	A		FREIGHTER	f	Obsidian hills is a large port in the north. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	18
130	B		Cook	f	Find Jin west of 130	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	19
130	C			f	Dangerous creatures east of 130 on little rocky island with dead trees	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	20
130	D	Pollen		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	21
7	1 B	Freighter	Picture	f	Old dead manticore. Coordinates to volcano near Lukra city. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	22
59	B			f	Gained low morale, lost 1 command	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	23
121	A	Diving suit token		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	24
121	B			f	Gain material 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	25
40	A		Letter	f	Deliver letter to village in northern mountains. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	26
40	B	Guide		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	27
40	D	Earthquake		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	28
40		Burn		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	29
40		Thug		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	30
22	A		Cinder	f	On island west with 2 volcanoes	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	31
29		Expected		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	32
29	1			f	Trade goods to gain xp 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	33
102		Basement	Basement	f	Lots of goods!	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	34
12	1 A	Cinder	Prince	f	Saved tholao mastiff. Take him to Lukra 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	35
12	1 A	Cinder	Prince	f	Saved tholao mastiff. Take him to Lukra 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	36
78		LAUNCH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	37
78		LIFT		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	38
78		LANDING		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	39
78				f	COMBAT (L16). Gain 4 coins, 2 meat, 1 material, 3 XP	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	40
78	A		LIFT	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	41
58	C A		PASSWORD	f	Requires 2coins. Password Raltolde - related to unique item to be sold. Bring $. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	42
58	D			f	Pay 1 coin, gain 2 meat, 2 veg 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	43
107	A			f		f	0	2 grain	1 coin	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	44
107		LIFT	LANDING	f		f	0	5 coins, 2 artifacts. 		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	45
132	1 A, 5	AUCTION		f		f	0	2 veg		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	46
69	A 1 A			f		t	18	5 coins, 2 meat, 1 material, 1 artifact, 4 XP		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	47
60	A 1 C 4	MATERIALS	CLOCK	f	Complete MATERIALS. 	f	0	Totem: stone of bargaining		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	48
42	B	CRYSTAL		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	49
115			AIRSHIP	f	Gain 1 ship damage. Crashed airship. Search craft by landing on beach north of 115	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	50
103		AIRSHIP		f	Picked up a Makrazan boy named Meelo. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	51
103	1 B		THUG	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	52
103	4 		GOAT	f	Competed AIRSHIP. Gained 2 material, 2 coins, 2 XP	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	53
41		COOK		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	54
41	7 			f	Gained adventure card 6. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	55
41	1 A			f	Leads to combat (L12)	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	56
41	6 A			f	Gain 8 coins, 1 material, 4 XP 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	57
70	D	PRINCE		f	Unavailable if BANISHED 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	58
70	3 B, 5 B			f	Gain 5 coins, 2 XP, stone of mending totem, complete PRINCE. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	59
70	A			f	Gain diving suit token for 5 coins. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	60
70	B	PYRAMID	SCIENCE	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	61
70	B		SCIENCE	f	Find science ship SW of Lukra city (70). 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	62
70	C	HIVE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	63
87	3 A	SCIENCE	HIVE	f	Combat (L14). Gain 6 coins, complete SCIENCE	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	64
70	C	HIVE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	65
70	2 B	HIVE		f	Gained -4 health, 1 coin, 1 weakened status	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	66
70	2 C	HIVE		f	Gain 2 low morale	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	67
70	2 A	HIVE		f	Gained -6 health	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	68
70	2 D	HIVE		f	Combat (L15), gain 4 coins, 1 artifact, 3XP, totem Orfash Axe of Cinderlands. Complete HIVE. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	69
77		LIBRARY		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	70
77	A		RUINED	f	COMBAT (L18). Gain 6 coins, 1 material, 5 XP, totem Meecra - book of fame and infame. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	71
60	A			f	Meet Raziz Ven, mayor of Glance. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	72
60	1 A		CRYSTAL	f	Unavailable if CRYSTAL, MATERIALS, or CLOCK. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	73
60	1A		CRYSTAL	f	Find CRYSTAL in mine N of glance or from an artist E of glance. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	74
60	B C			f	Unavailable if PASSWORD or AUCTION. Need 2 coins to get PASSWORD. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	75
60	B D			f	Spend 1 coin to gain 2 meat and 2 veg. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	76
60	C	HEALER		f	Vilmus Oleberos	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	77
60	D	LETTER	DAGGER	f	Gain adventure card (Zvarm), complete LETTER. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	78
76		GOAT		f	Bad. Lost 1 food, 1 coin, 1 material, Lose quest 126. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	79
76		PICTURE	FATHER	f	Gain 1 meat, 2 XP, market card, complete PICTURE	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	80
76		PICTURE	FATHER	f	FATHER - go south in the strait NW of Hunter’s Haven. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	81
77		RUINED		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	82
60	D		DAGGER	f	Go forest island south of the great pillars to the east. 	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	83
107		LAUNCH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	84
107		LIFT		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	85
132		AUCTION		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	86
132	A	PASSWORD		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	87
132	B			f	Gain 1 coin	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	88
129	A	SAGE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	89
114		EXTINGUISHED		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	90
114	A 1 B	PATH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	91
180	A 1 B 		ENEMY	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	92
86		TRIVIAL		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	93
86	1 A C B A			f		f	0		1 frightened or madness	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	94
172				f		f	0			0	0	0	0	0	0	0	0	1	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	233
201	A		REMINISICE	f		f	0	2 grain, 1 material, 2 veg	Remove morale	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	96
1	2 B 4 A	PATH		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	97
165	A			f		f	0			0	0	0	0	0	0	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CRAFT	5		0	0	99
149		HERETIC GOMKA WANDERED		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	100
149	A		HERETIC	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	101
149		HERETIC		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	102
84	A	MIRRORS		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	103
84	B			f		f	0			0	0	0	1	0	1	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	104
24	B		KEMTER SAPLING	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CRAFT	5		0	0	106
24		KEMTER		t		f	11			0	0	0	0	0	0	0	0	0	0	0	3	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	108
146		PINES		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	109
24		KEMTER		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	110
170	A			f		f	0	2 grain	1 coin	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	111
132	A B A	PASSWORD	AUCTION	f		f	0	Adventure card. Complete PASSWORD. 		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	112
78	4 A	LANDING		f		f	0	2 coin	1 material	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	113
69	5 A 	CRYSTAL	MATERIALS	f	Complete CRYSTAL. 	f	0	2 coins, 2 XP		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	114
60	A 1 B	OWL		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	115
60	A			f		f	0	2 coins		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	116
129	A 1			f		f	0	1 veg		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	117
114		HONOR		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	118
114	A 1 A 7 D 		HONOR IMMORTAL	f		f	0	2 XP 		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	119
180		ENEMY MONSTER		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	120
180	A 1 A		MONSTER	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	121
86	A		TRIVIAL	f		t	16	3 coins, 1 meat, 1 artifact, 3 xp 		0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	122
120	A		TRUNK	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	123
201		REMINISCE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	0	124
172	4	PROSPECTOR	RUSH	t		f	21			0	0	0	0	0	8	0	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	234
84	A 1A	MIRRORS		t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	SAVVY	10	Stone of many eyes	56	0	240
2	A		PINK	t		f	0			0	0	0	0	0	4	0	0	0	0	0	0	0	0	0	1	0	0	0	1	0	0	0	0	0	0	0	0		0		0	0	128
146	A 1 A 3 A		ARCTIC PINES	f	Gain adventure card Alexei bespalov 	f	0			0	0	0	0	0	0	0	0	0	0	0	3	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	129
24	A		KEMTER GROWTH	f		f	0			0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	SAVVY	7		0	0	130
0				f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	235
155	A7B2A3A	HERETIC	CHOIR	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	176
137	B	TRUNK		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	177
137	B2C	TRUNK		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		85	0	178
158	A2A4	DAGGER		f		f	0			0	0	0	0	0	0	2	2	0	2	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CUNNING	8		0	0	179
113	B	TRICKY		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	180
1132	A2			f		f	0			0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	181
113	A2			f		f	0			0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	182
85	B	TOWER		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	183
85	1A			f		f	13			0	0	0	0	0	6	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	184
106	A	STONE		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	185
128	B	CHOIR		f		f	13			0	0	0	0	0	0	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0	Meecras guitar	86	0	186
165	C2B	GROWTH		f		f	0			0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CUNNING	8		0	0	187
24	B		KEMTER SAPLING	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CRAFT	5		0	0	199
206	4	RUST		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	236
206	A		RUST HARPOON	t	If fail, lose 7 health and gain nothing	f	0			0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CUNNING	6		0	0	237
213	2	ROBOT	MIRRORS	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	238
120	B2B	SAPLING	GROWTH	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	204
120	B2B	SAPLING	GROWTH	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	206
165	BA	GROWTH		t		f	17			0	0	0	0	0	4	0	1	0	0	0	1	3	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	PERCEPTION	10	Life seed	32	0	210
201	A		REMINISISCE	f		f	0			0	0	0	0	0	0	0	2	2	0	0	1	0	0	0	0	0	0	0	0	0	0	9	0	0	0	0	0		0		0	0	213
155	B			t		f	0			0	0	0	0	0	0	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	PERCEPTION	6		0	0	215
160	C	ICE ARCTIC		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	217
160	B	MEDICINE		f		f	0			2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	218
160	A 1A		PROSPECTOR	t		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	2	0	0	0	0	0		0		0	0	221
157	B		HUBRIS	t		f	14			0	0	0	0	0	5	0	0	0	0	0	0	3	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	222
157		HUBRIS		t		f	0			1	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	223
199		JUNK		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	224
199	A		ROBOT JUNK	t	This adventure card is bad - gain low morale when explore	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	CRAFT	6		20	0	225
199		JUNK		f		f	0			0	0	0	0	0	0	2	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	226
181	B	BLOOD		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	227
181	A		HERRING	t	Find cottage east of 181	f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	228
151	A 1C	FEAST		f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	229
151	A 1A		FAMINE	f		f	0			0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0		0		0	0	230
\.


--
-- Data for Name: sleeping_gods_totems; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sleeping_gods_totems (id, totem, found) FROM stdin;
55	Nautilus Stone (Dungeons)	f
20	Stone of Bargaining	t
52	Mystic's Idol (Ruin)	f
49	Meecra's Salt	f
79	4 (Quests 171 - 172)	t
40	Lava Sword (Ruin)	f
37	Key Stone	f
34	Hunter's Pebble (Ruin)	f
31	God Stone	f
28	Gate Stone	f
46	Meecra's Guitar	t
5	Raltoldes's Spear	f
6	Stone of Roaming	f
9	Stone of Sacrifice	f
11	Shorme's Hammer	f
12	Stone of Screaming (Ruin)	f
25	Fish Bone Spear (Dungeons)	f
8	Shadow Lantern (Ruin)	f
22	Ethereal Mask (Dungeons)	f
14	Snake Bangle	f
15	Stone of Shanties	f
17	Stone of Absence (Ruin)	f
18	Stone of Spirits (Ruin)	f
19	Cursed Ruby (Ruin)	f
16	Clockwork Owl	f
95	#11	f
21	Stone of Squids	f
23	Stone of Blood	f
24	Stone of Storms	f
26	Stone of Cats	f
27	Stone of the Deep	f
29	Stone of Chains	f
30	Stone of the Hunt	f
32	Stone of Changing (Dungeons)	f
33	Stone of the Mind	f
35	Stone of Deceit	f
36	Stone of the Wind	f
38	Stone of Earthquakes	f
39	Stone of the Wind & Waves	f
41	Stone of Fitness	f
42	Stone of Teeth (Ruin)	f
44	Stone of Freezing	f
45	Stone of Time	f
47	Stone of Gluttony	f
48	Stone of Undeath	f
50	Stone of Healing	f
51	Stone of Vengeance (Ruin)	f
54	Stone of Vim (Dungeons)	f
56	Stone of Madness	f
58	Nightmare Stone (Ruin)	f
60	Stone of Worldly Sorrows (Ruin)	f
61	Obsidian Greaves (Dungeons)	f
64	Obsidian Heart	f
65	Stone of Mirrors (Ruin)	f
67	Ohmludes's Crystal	f
70	Pigment Stone (Ruin)	f
73	Puzzle Box	f
76	Raltolde's Shield	f
92	#10	f
87	#1	t
43	Life Seed	t
82	7 (Quests 169-170)	t
89	#9	f
57	Stone of Weakness	f
53	Stone of the Lost (Ruin)	f
59	Stone of many Eyes	t
88	#5	f
91	#6	f
94	#7	f
97	#8	f
98	#12	f
90	#2	f
93	#3	f
96	#4	f
99	#13	f
77	Stone of Riddles	f
74	Stone of Mist (Ruin)	f
71	Stone of Music	f
68	Stone of Muscle	f
63	Sword of the Duelist	f
66	The Perpetual Flame	f
69	Thrack's Charm	f
72	Valard's Prism (Ruin)	f
75	Zacra's Mask	f
78	Zrell Stone (Ruin)	f
7	Blade of Thrack	f
13	Centipede Crown (Ruin)	f
85	9 (Quest 168)	f
80	11 (Quest 174)	f
83	13 (Quest 175)	f
86	15 (Quests 176-177)	f
81	18 (Quest 178-180)	f
84	22 (Quest 173)	f
62	Stone of Mending	t
10	Book of Fame and Infame	t
2	Axe of the Cinderlands	t
\.


--
-- Name: games_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.games_id_seq', 3896, true);


--
-- Name: sleeping_gods_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.sleeping_gods_id_seq', 240, true);


--
-- Name: sleeping_gods_totems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.sleeping_gods_totems_id_seq', 99, true);


--
-- Name: games games_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT games_pkey PRIMARY KEY (id);


--
-- Name: sleeping_gods sleeping_gods_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sleeping_gods
    ADD CONSTRAINT sleeping_gods_pkey PRIMARY KEY (id);


--
-- Name: sleeping_gods_totems sleeping_gods_totems_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sleeping_gods_totems
    ADD CONSTRAINT sleeping_gods_totems_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict sfOLOIStoCNhxvapnz9LBbgEiI04a2OirMN6tx7bJyusJxibKfaPQgfjlgfHA7i

