--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

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
-- Name: ai_summaries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ai_summaries (
    id integer NOT NULL,
    company_id integer NOT NULL,
    summary_text text,
    summary_language character varying(10),
    model_version character varying(50),
    topics jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ai_summaries OWNER TO postgres;

--
-- Name: ai_summaries_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ai_summaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ai_summaries_id_seq OWNER TO postgres;

--
-- Name: ai_summaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ai_summaries_id_seq OWNED BY public.ai_summaries.id;


--
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    business_id character varying(255),
    display_name character varying(255),
    website_url text,
    logo_url text,
    star_rating_svg character varying(500),
    total_reviews integer,
    trust_score numeric(3,2),
    stars integer,
    is_claimed boolean,
    categories jsonb,
    verification jsonb,
    contact_info jsonb,
    activity jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO postgres;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    company_id integer NOT NULL,
    review_id character varying(255) NOT NULL,
    rating integer,
    title text,
    text text,
    text_en text,
    author_name character varying(255),
    author_id character varying(255),
    author_country_code character varying(10),
    author_review_count integer,
    review_date timestamp without time zone,
    experience_date date,
    verified boolean DEFAULT false,
    language character varying(10),
    reply_message text,
    reply_date timestamp without time zone,
    likes integer DEFAULT 0,
    source character varying(50),
    labels jsonb,
    scraped_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_edited boolean DEFAULT false
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO postgres;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topics (
    id integer NOT NULL,
    topic_key character varying(100) NOT NULL,
    topic_name character varying(255) NOT NULL,
    search_terms text[] NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.topics OWNER TO postgres;

--
-- Name: topics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topics_id_seq OWNER TO postgres;

--
-- Name: topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topics_id_seq OWNED BY public.topics.id;


--
-- Name: ai_summaries id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_summaries ALTER COLUMN id SET DEFAULT nextval('public.ai_summaries_id_seq'::regclass);


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: topics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics ALTER COLUMN id SET DEFAULT nextval('public.topics_id_seq'::regclass);


--
-- Name: ai_summaries ai_summaries_company_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_summaries
    ADD CONSTRAINT ai_summaries_company_id_key UNIQUE (company_id);


--
-- Name: ai_summaries ai_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_summaries
    ADD CONSTRAINT ai_summaries_pkey PRIMARY KEY (id);


--
-- Name: companies companies_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_name_key UNIQUE (name);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_review_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_review_id_key UNIQUE (review_id);


--
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (id);


--
-- Name: topics topics_topic_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_topic_key_key UNIQUE (topic_key);


--
-- Name: idx_ai_summaries_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ai_summaries_company ON public.ai_summaries USING btree (company_id);


--
-- Name: idx_reviews_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reviews_company ON public.reviews USING btree (company_id);


--
-- Name: idx_reviews_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reviews_date ON public.reviews USING btree (review_date);


--
-- Name: idx_reviews_scraped; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reviews_scraped ON public.reviews USING btree (scraped_at);


--
-- Name: idx_topics_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topics_key ON public.topics USING btree (topic_key);


--
-- Name: ai_summaries ai_summaries_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_summaries
    ADD CONSTRAINT ai_summaries_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--