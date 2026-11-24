using System.Text.Json;
using Ser.Approval;
if(args.Contains("--selftest")){SelfTest.Run();return;}
var builder=WebApplication.CreateBuilder(args);builder.WebHost.UseUrls("http://127.0.0.1:8832");builder.WebHost.ConfigureKestrel(o=>o.Limits.MaxRequestBodySize=16384);var app=builder.Build();
var file=Path.Combine(AppContext.BaseDirectory,"data","approval.json");var store=new Store(file);store.Seed();
app.Use(async(context,next)=>{try{await next();}catch(Exception e){context.Response.StatusCode=400;await context.Response.WriteAsJsonAsync(new{error=e.Message});}});
app.MapGet("/api/approval",()=>new{requests=store.List(),budget=150000,reserved=store.Reserved()});
app.MapPost("/api/approval/create",(CreateRequest b)=>store.Create(b));
app.MapPost("/api/approval/action",(ActionRequest b)=>store.Act(b));
app.Run();
namespace Ser.Approval {
public record Entry(int Id,string Title,string Department,string Author,int Amount,string State,int Version,List<string> History);
public record CreateRequest(string Title,string Department,string Author,int Amount);
public record ActionRequest(int Id,int Version,string Actor,string Action,string Reason);
public class Store {
 readonly string? file;readonly object gate=new();List<Entry> entries=[];
 public Store(string? filename=null){file=filename;if(file!=null&&File.Exists(file))entries=JsonSerializer.Deserialize<List<Entry>>(File.ReadAllText(file))??[];}
 public List<Entry> List(){lock(gate)return entries.Select(x=>x with{History=[..x.History]}).OrderByDescending(x=>x.Id).ToList();}
 public int Reserved(){lock(gate)return entries.Where(x=>x.State is "Согласовано" or "Оплачено").Sum(x=>x.Amount);}
 void Commit(List<Entry> next){if(file!=null){Directory.CreateDirectory(Path.GetDirectoryName(file)!);var temp=file+".tmp";File.WriteAllText(temp,JsonSerializer.Serialize(next));File.Move(temp,file,true);}entries=next;}
 public Entry Create(CreateRequest b){lock(gate){if(string.IsNullOrWhiteSpace(b.Title)||b.Title.Length>120||!new[]{"Анна","Марк","Ирина"}.Contains(b.Author)||!new[]{"Операции","Продажи","Разработка"}.Contains(b.Department)||b.Amount<1||b.Amount>1000000)throw new ArgumentException("Проверьте название, отдел, автора и сумму (1–1 000 000 ₽)");var e=new Entry(entries.Count==0?1:entries.Max(x=>x.Id)+1,b.Title.Trim(),b.Department,b.Author,b.Amount,"На согласовании",1,["Заявка создана · "+b.Author]);Commit([..entries,e]);return e;}}
 public Entry Act(ActionRequest b){lock(gate){var old=entries.SingleOrDefault(x=>x.Id==b.Id)??throw new ArgumentException("Заявка не найдена");if(old.Version!=b.Version)throw new ArgumentException("Заявка уже изменена. Обновите список.");string state;
 if(b.Action=="approve"){if(b.Actor!="Руководитель"||old.State!="На согласовании")throw new ArgumentException("Согласование недоступно для этой роли или этапа");if(Reserved()+old.Amount>150000)throw new ArgumentException("Недостаточно бюджета: лимит периода 150 000 ₽");state="Согласовано";}
 else if(b.Action=="reject"){if(b.Actor!="Руководитель"||old.State!="На согласовании"||string.IsNullOrWhiteSpace(b.Reason)||b.Reason.Length>300)throw new ArgumentException("Для отказа руководитель должен указать причину (до 300 символов)");state="Отклонено";}
 else if(b.Action=="pay"){if(b.Actor!="Бухгалтер"||old.State!="Согласовано")throw new ArgumentException("Оплату может отметить бухгалтер после согласования");state="Оплачено";}
 else throw new ArgumentException("Неизвестное действие");
 var updated=old with{State=state,Version=old.Version+1,History=[..old.History,state+" · "+b.Actor+(b.Action=="reject"?" · "+b.Reason:"")]};Commit(entries.Select(x=>x.Id==old.Id?updated:x).ToList());return updated;}}
 public void Seed(){lock(gate){if(entries.Count>0)return;Create(new("Лицензии для команды","Разработка","Марк",24000));Create(new("Рабочие кресла","Операции","Анна",46000));Create(new("Материалы для презентации","Продажи","Ирина",12000));Create(new("Обновление оборудования","Разработка","Марк",92000));Act(new(1,1,"Руководитель","approve",""));Act(new(1,2,"Бухгалтер","pay",""));Act(new(2,1,"Руководитель","approve",""));}}
}
public static class SelfTest {
 public static void Run(){int n=0;void Check(bool ok,string name){if(!ok)throw new Exception(name);Console.WriteLine("PASS "+name);n++;}bool Reject(Action f){try{f();return false;}catch(ArgumentException){return true;}}
 var s=new Store();var e=s.Create(new("Тест","Операции","Анна",100000));Check(Reject(()=>s.Act(new(e.Id,1,"Бухгалтер","approve",""))),"role enforced");Check(Reject(()=>s.Act(new(e.Id,1,"Бухгалтер","pay",""))),"cannot pay before approval");Check(Reject(()=>s.Act(new(e.Id,1,"Руководитель","reject",""))),"rejection reason required");s.Act(new(e.Id,1,"Руководитель","approve",""));Check(s.Reserved()==100000,"approved expense reserves budget");Check(Reject(()=>s.Act(new(e.Id,1,"Руководитель","approve",""))),"stale action rejected");var second=s.Create(new("Тест 2","Операции","Анна",60000));Check(Reject(()=>s.Act(new(second.Id,1,"Руководитель","approve",""))),"budget enforced");s.Act(new(e.Id,2,"Бухгалтер","pay",""));Check(s.Reserved()==100000,"payment does not double reserve");s.Act(new(second.Id,1,"Руководитель","reject","Лимит исчерпан"));Check(s.List().First().History.Count==2,"history saved");Check(Reject(()=>s.Create(new("","Операции","Анна",1))),"invalid request rejected");
 var path=Path.Combine(Path.GetTempPath(),Guid.NewGuid()+".json");try{var disk=new Store(path);disk.Create(new("Сохранить","Продажи","Ирина",500));Check(new Store(path).List().Count==1,"restart persistence");}finally{if(File.Exists(path))File.Delete(path);}Console.WriteLine($"{n} checks passed");}
}
}
