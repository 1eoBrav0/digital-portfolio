package main

import (
	"encoding/csv"
	"encoding/json"
	"encoding/xml"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type Item struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Date    string `json:"date"`
	Source  string `json:"source"`
	Summary string `json:"summary"`
}
type Report struct {
	Items      []Item   `json:"items"`
	Read       int      `json:"read"`
	Duplicates int      `json:"duplicates"`
	Filtered   int      `json:"filtered"`
	Errors     []string `json:"errors"`
}
type RSS struct {
	XMLName xml.Name
	Channel struct {
		Title string `xml:"title"`
		Items []struct {
			Title       string `xml:"title"`
			Link        string `xml:"link"`
			Date        string `xml:"pubDate"`
			Description string `xml:"description"`
		} `xml:"item"`
	} `xml:"channel"`
}
type Atom struct {
	XMLName xml.Name
	Title   string `xml:"title"`
	Entries []struct {
		Title string `xml:"title"`
		Links []struct {
			Href string `xml:"href,attr"`
			Rel  string `xml:"rel,attr"`
		} `xml:"link"`
		Date    string `xml:"updated"`
		Summary string `xml:"summary"`
	} `xml:"entry"`
}

func canonical(raw string) (string, error) {
	u, e := url.Parse(strings.TrimSpace(raw))
	if e != nil || u.Hostname() == "" || (u.Scheme != "https" && u.Scheme != "http") || u.User != nil {
		return "", errors.New("небезопасная или некорректная ссылка")
	}
	u.Fragment = ""
	u.Host = strings.ToLower(u.Host)
	q := u.Query()
	for k := range q {
		if strings.HasPrefix(strings.ToLower(k), "utm_") {
			q.Del(k)
		}
	}
	u.RawQuery = q.Encode()
	return u.String(), nil
}
func date(raw string) string {
	for _, layout := range []string{time.RFC3339, time.RFC1123Z, time.RFC1123, time.RFC822Z, "2006-01-02"} {
		if t, e := time.Parse(layout, strings.TrimSpace(raw)); e == nil {
			return t.UTC().Format(time.RFC3339)
		}
	}
	return ""
}
func parse(data []byte, source string) ([]Item, error) {
	if len(data) > 2*1024*1024 {
		return nil, errors.New("файл больше 2 МБ")
	}
	if strings.Contains(strings.ToUpper(string(data)), "<!DOCTYPE") || strings.Contains(strings.ToUpper(string(data)), "<!ENTITY") {
		return nil, errors.New("DTD и сущности запрещены")
	}
	var probe struct{ XMLName xml.Name }
	if e := xml.Unmarshal(data, &probe); e != nil {
		return nil, e
	}
	out := []Item{}
	if probe.XMLName.Local == "rss" {
		var r RSS
		if e := xml.Unmarshal(data, &r); e != nil {
			return nil, e
		}
		for _, i := range r.Channel.Items {
			out = append(out, Item{strings.TrimSpace(i.Title), i.Link, date(i.Date), source, strings.TrimSpace(i.Description)})
		}
	} else if probe.XMLName.Local == "feed" {
		var a Atom
		if e := xml.Unmarshal(data, &a); e != nil {
			return nil, e
		}
		for _, i := range a.Entries {
			link := ""
			for _, l := range i.Links {
				if l.Rel == "alternate" || l.Rel == "" {
					link = l.Href
					break
				}
			}
			out = append(out, Item{strings.TrimSpace(i.Title), link, date(i.Date), source, strings.TrimSpace(i.Summary)})
		}
	} else {
		return nil, errors.New("ожидается RSS 2.0 или Atom")
	}
	if len(out) > 5000 {
		return nil, errors.New("больше 5000 записей")
	}
	return out, nil
}
func merge(sources map[string][]byte, query string) Report {
	r := Report{Items: []Item{}, Errors: []string{}}
	seen := map[string]bool{}
	keys := []string{}
	for k := range sources {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, name := range keys {
		items, e := parse(sources[name], name)
		if e != nil {
			r.Errors = append(r.Errors, name+": "+e.Error())
			continue
		}
		for _, i := range items {
			r.Read++
			u, e := canonical(i.URL)
			if e != nil || i.Title == "" {
				r.Errors = append(r.Errors, name+": пропущена запись без заголовка или корректной ссылки")
				continue
			}
			i.URL = u
			if seen[u] {
				r.Duplicates++
				continue
			}
			seen[u] = true
			if query != "" && !strings.Contains(strings.ToLower(i.Title+" "+i.Summary), strings.ToLower(query)) {
				r.Filtered++
				continue
			}
			r.Items = append(r.Items, i)
		}
	}
	sort.SliceStable(r.Items, func(i, j int) bool {
		if r.Items[i].Date == r.Items[j].Date {
			return r.Items[i].URL < r.Items[j].URL
		}
		return r.Items[i].Date > r.Items[j].Date
	})
	return r
}
func readSources(dir string) (map[string][]byte, error) {
	files, e := filepath.Glob(filepath.Join(dir, "*.xml"))
	if e != nil {
		return nil, e
	}
	if len(files) == 0 {
		return nil, errors.New("нет XML файлов")
	}
	out := map[string][]byte{}
	for _, p := range files {
		f, e := os.Open(p)
		if e != nil {
			return nil, e
		}
		b, e := io.ReadAll(io.LimitReader(f, 2*1024*1024+1))
		f.Close()
		if e != nil {
			return nil, e
		}
		out[filepath.Base(p)] = b
	}
	return out, nil
}
func csvCell(s string) string {
	if strings.ContainsAny(strings.TrimLeft(s, " \t")[:min(1, len(strings.TrimLeft(s, " \t")))], "=+-@") {
		return "'" + s
	}
	return s
}
func main() {
	serve := flag.Bool("serve", false, "local UI API on8833")
	dir := flag.String("input", "fixtures", "directory with RSS/Atom XML")
	query := flag.String("query", "", "case-insensitive substring")
	output := flag.String("out", "", "new JSON output file")
	flag.Parse()
	if *serve {
		mux := http.NewServeMux()
		mux.HandleFunc("/api/feed", func(w http.ResponseWriter, req *http.Request) {
			w.Header().Set("Content-Type", "application/json; charset=utf-8")
			var sources map[string][]byte
			var e error
			if req.Method == "POST" {
				req.Body = http.MaxBytesReader(w, req.Body, 2*1024*1024)
				var body struct {
					Name  string `json:"name"`
					XML   string `json:"xml"`
					Query string `json:"query"`
				}
				e = json.NewDecoder(req.Body).Decode(&body)
				sources = map[string][]byte{body.Name: []byte(body.XML)}
				if e == nil {
					json.NewEncoder(w).Encode(merge(sources, body.Query))
					return
				}
			} else {
				sources, e = readSources(*dir)
			}
			if e != nil {
				w.WriteHeader(400)
				json.NewEncoder(w).Encode(map[string]string{"error": e.Error()})
				return
			}
			json.NewEncoder(w).Encode(merge(sources, req.URL.Query().Get("query")))
		})
		s := &http.Server{Addr: "127.0.0.1:8833", Handler: mux, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second}
		fmt.Println("Radar http://127.0.0.1:8833")
		if e := s.ListenAndServe(); e != nil {
			panic(e)
		}
		return
	}
	sources, e := readSources(*dir)
	if e != nil {
		panic(e)
	}
	r := merge(sources, *query)
	b, e := json.MarshalIndent(r, "", "  ")
	if e != nil {
		panic(e)
	}
	if *output == "" {
		fmt.Println(string(b))
	} else {
		f, e := os.OpenFile(*output, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if e != nil {
			panic(e)
		}
		_, e = f.Write(b)
		f.Close()
		if e != nil {
			panic(e)
		}
		c, e := os.OpenFile(*output+".csv", os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if e != nil {
			panic(e)
		}
		w := csv.NewWriter(c)
		w.Write([]string{"title", "url", "date", "source"})
		for _, i := range r.Items {
			w.Write([]string{csvCell(i.Title), i.URL, i.Date, csvCell(i.Source)})
		}
		w.Flush()
		e = w.Error()
		c.Close()
		if e != nil {
			panic(e)
		}
	}
}
