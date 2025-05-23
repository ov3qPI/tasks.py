import json
import argparse
import os
import datetime
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, Completion

class TaskManager:
    def __init__(self, file_path="/storage/emulated/0/Documents/.todo.json"):
        self.file_path = file_path
    def load_tasks(self):
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r") as f:
            return json.load(f)
    def save_tasks(self, tasks):
        with open(self.file_path, "w") as f:
            json.dump(tasks, f, indent=2)
    def get_all_tags(self, tasks):
        tags = set()
        for task in tasks:
            tags.update(task.get("tags", []))
        return sorted(tags)

class ExclusionWordCompleter(WordCompleter):
    def get_completions(self, document, complete_event):
        text = document.get_word_before_cursor(WORD=True)
        if text.startswith("-"):
            prefix = "-"
            text = text[1:]
            start_position = -len(document.get_word_before_cursor(WORD=True))
            for word in self.words:
                if word.lower().startswith(text.lower()):
                    yield Completion(prefix + word, start_position=start_position)
        else:
            yield from super().get_completions(document, complete_event)

def prompt_for_tags(existing_tags, default_tags=None):
    completer = ExclusionWordCompleter(existing_tags, ignore_case=True, sentence=True)
    default = " ".join(default_tags) if default_tags else ""
    tag_input = prompt("Tags: ", completer=completer, default=default)
    return tag_input.strip().split()

def add_tasks(task_manager, tasks_with_tags):
    tasks = task_manager.load_tasks()
    max_id = max((task["id"] for task in tasks), default=0)
    for i, (title, tags) in enumerate(tasks_with_tags):
        task = {"id": max_id + i + 1, "title": title, "tags": tags}
        tasks.append(task)
        print(f"Added: {task['id']} {title} with tags {tags}")
    task_manager.save_tasks(tasks)

def add_tag_to_tasks(task_manager, tag, task_ids):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] in task_ids:
            if tag not in task["tags"]:
                task["tags"].append(tag)
                print(f"Added tag '{tag}' to task {task['id']}: {task['title']}")
                updated = True
            else:
                print(f"Task {task['id']} already has tag '{tag}'")
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def delete_tag_from_tasks(task_manager, tag, task_ids):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] in task_ids:
            if tag in task.get("tags", []):
                task["tags"].remove(tag)
                print(f"Removed tag '{tag}' from task {task['id']}: {task['title']}")
                updated = True
            else:
                print(f"Task {task['id']} does not have tag '{tag}'")
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def delete_reliance_on(task_manager, dependency_id):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if "reliance" in task and dependency_id in task["reliance"]:
            task["reliance"].remove(dependency_id)
            print(f"Removed reliance on {dependency_id} from task {task['id']}: {task['title']}")
            updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def delete_reliance_for(task_manager, task_id):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] == task_id and "reliance" in task:
            del task["reliance"]
            print(f"Removed all reliance from task {task_id}: {task['title']}")
            updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def add_reliance(task_manager, source_ids, target_ids):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] in source_ids:
            if "reliance" not in task:
                task["reliance"] = []
            for dep in target_ids:
                if dep not in task["reliance"]:
                    task["reliance"].append(dep)
                    print(f"Task {task['id']} is now reliant on {dep}")
                    updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def add_multiple_reliances(task_manager, tokens):
    tasks = task_manager.load_tasks()
    updated = False
    groups = []
    current_group = []
    for token in tokens:
        if token == "||":
            if current_group:
                groups.append(current_group)
                current_group = []
        else:
            current_group.append(token)
    if current_group:
        groups.append(current_group)
    for group in groups:
        try:
            on_index = group.index("on")
        except ValueError:
            print("Missing 'on' keyword in reliance command for group:", group)
            continue
        left_tokens = group[:on_index]
        right_tokens = group[on_index+1:]
        if not left_tokens or not right_tokens:
            print("Invalid reliance command format in group:", group)
            continue
        if len(left_tokens) == 1:
            try:
                source_ids = [int(left_tokens[0])]
                target_ids = list(map(int, right_tokens))
            except ValueError:
                print("Task IDs must be integers in group:", group)
                continue
        elif len(right_tokens) == 1:
            try:
                source_ids = list(map(int, left_tokens))
                target_ids = [int(right_tokens[0])]
            except ValueError:
                print("Task IDs must be integers in group:", group)
                continue
        else:
            print("Invalid reliance command format in group:", group)
            continue
        for task in tasks:
            if task["id"] in source_ids:
                if "reliance" not in task:
                    task["reliance"] = []
                for dep in target_ids:
                    if dep not in task["reliance"]:
                        task["reliance"].append(dep)
                        print(f"Task {task['id']} is now reliant on {dep}")
                        updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def add_time_reliance(task_manager, tokens):
    if len(tokens) < 2:
        print("Usage: tasks.py add reliance time {begin date} [end date] <task id> [<task id> ...]")
        return
    try:
        begin_date = datetime.datetime.strptime(tokens[0], "%Y-%m-%d").date()
    except ValueError:
        print("Error: Begin date must be in YYYY-MM-DD format.")
        return
    end_date = None
    try:
        end_date = datetime.datetime.strptime(tokens[1], "%Y-%m-%d").date()
        task_id_tokens = tokens[2:]
    except ValueError:
        task_id_tokens = tokens[1:]
    if not task_id_tokens:
        print("No task IDs provided for time reliance. Please specify one or more task IDs.")
        return
    try:
        task_ids = list(map(int, task_id_tokens))
    except ValueError:
        print("Task IDs must be integers.")
        return
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] in task_ids:
            task["time_reliance"] = {"begin": begin_date.strftime("%Y-%m-%d")}
            if end_date is not None:
                task["time_reliance"]["end"] = end_date.strftime("%Y-%m-%d")
            print(f"Task {task['id']} is now time-reliant: {task['time_reliance']}")
            updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")
 
def hide_task(task_manager, task_id, days):
    tasks = task_manager.load_tasks()
    updated = False
    for task in tasks:
        if task["id"] == task_id:
            hide_until = datetime.date.today() + datetime.timedelta(days=days)
            task["hide_until"] = hide_until.strftime("%Y-%m-%d")
            print(f"Task {task['id']} hidden until {task['hide_until']}")
            updated = True
    if updated:
        task_manager.save_tasks(tasks)
    else:
        print("No tasks were updated.")

def list_tasks_by_search(task_manager):
    tasks = task_manager.load_tasks()
    all_tags = task_manager.get_all_tags(tasks)
    completer = ExclusionWordCompleter(all_tags + [task["title"] for task in tasks], ignore_case=True, sentence=True)
    search_input = prompt("Search tasks (title or tags): ", completer=completer).lower()
    terms = search_input.split()
    include_reliant = False
    if "+reliant" in terms:
        include_reliant = True
        terms.remove("+reliant")
    show_tags = False
    if "+tags" in terms:
        show_tags = True
        terms.remove("+tags")
    include_terms = [term for term in terms if not term.startswith("-")]
    exclude_terms = [term[1:] for term in terms if term.startswith("-")]
    today = datetime.date.today()
    for task in tasks:
        if "hide_until" in task:
            try:
                hide_date = datetime.datetime.strptime(task["hide_until"], "%Y-%m-%d").date()
                if today < hide_date:
                    continue
            except:
                pass
        if not include_reliant and task.get("reliance"):
            continue
        if "time_reliance" in task:
            try:
                begin = datetime.datetime.strptime(task["time_reliance"]["begin"], "%Y-%m-%d").date()
                end = None
                if "end" in task["time_reliance"]:
                    end = datetime.datetime.strptime(task["time_reliance"]["end"], "%Y-%m-%d").date()
                if today < begin or (end is not None and today > end):
                    continue
            except Exception as e:
                print(f"Error parsing time_reliance for task {task['id']}: {e}")
        text = task["title"].lower() + " " + " ".join(task["tags"]).lower()
        if all(term in text for term in include_terms) and all(term not in text for term in exclude_terms):
            extra = ""
            if task.get("reliance"):
                extra = " | reliant on: " + ", ".join(map(str, task["reliance"]))
            if task.get("time_reliance"):
                extra += " | active between: " + task["time_reliance"]["begin"]
                if "end" in task["time_reliance"]:
                    extra += " and " + task["time_reliance"]["end"]
            if show_tags:
                print(f"{task['id']} {task['title']} | {', '.join(task['tags'])}{extra}")
            else:
                print(f"{task['id']} {task['title']}{extra}")

def delete_task(task_manager, task_id):
    tasks = task_manager.load_tasks()
    new_tasks = []
    for task in tasks:
        if task["id"] == task_id:
            continue
        if "reliance" in task:
            task["reliance"] = [dep for dep in task["reliance"] if dep != task_id]
        new_tasks.append(task)
    task_manager.save_tasks(new_tasks)
    print(f"Deleted task {task_id}")

def delete_all_tasks(task_manager):
    confirmation = prompt("Confirm delete all? [Y/n] ")
    if confirmation.lower() in ["y"]:
        task_manager.save_tasks([])
        print("Deleted all tasks.")
    else:
        print("Delete all tasks cancelled.")

def delete_range(task_manager, start_id, end_id):
    tasks = task_manager.load_tasks()
    new_tasks = []
    deleted_ids = set(range(start_id, end_id + 1))
    for task in tasks:
        if start_id <= task["id"] <= end_id:
            continue
        if "reliance" in task:
            task["reliance"] = [dep for dep in task["reliance"] if dep not in deleted_ids]
        new_tasks.append(task)
    task_manager.save_tasks(new_tasks)
    print(f"Deleted tasks from ID {start_id} to {end_id}")

def edit_task(task_manager, task_id=None):
    tasks = task_manager.load_tasks()
    if task_id is None:
        all_tags = task_manager.get_all_tags(tasks)
        completer = ExclusionWordCompleter(all_tags + [task["title"] for task in tasks], ignore_case=True, sentence=True)
        search_input = prompt("Search task to edit (title or tag): ", completer=completer).lower()
        matched_tasks = [task for task in tasks if search_input in task["title"].lower() or any(search_input in tag.lower() for tag in task["tags"])]
        if not matched_tasks:
            print("No matching tasks found.")
            return
        elif len(matched_tasks) == 1:
            task = matched_tasks[0]
        else:
            print("Multiple matches:")
            for t in matched_tasks:
                reliance_info = f" | reliant on: {', '.join(map(str, t.get('reliance', [])))}" if t.get("reliance") else ""
                time_info = ""
                if t.get("time_reliance"):
                    time_info = " | time window: " + t["time_reliance"]["begin"]
                    if "end" in t["time_reliance"]:
                        time_info += " to " + t["time_reliance"]["end"]
                print(f"{t['id']}. {t['title']}  Tags: {', '.join(t['tags'])}{reliance_info}{time_info}")
            try:
                task_id = int(prompt("Enter task ID to edit: "))
                task = next(t for t in tasks if t["id"] == task_id)
            except (ValueError, StopIteration):
                print("Invalid task ID.")
                return
    else:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            print("Task not found.")
            return
    new_title = prompt("Title: ", default=task["title"]).strip()
    new_tags = prompt_for_tags(task_manager.get_all_tags(tasks), default_tags=task["tags"])
    task["title"] = new_title or task["title"]
    task["tags"] = new_tags
    task_manager.save_tasks(tasks)
    print(f"Updated task {task['id']}")

def main():
    parser = argparse.ArgumentParser(description="Taggable CLI To-Do List")
    subparsers = parser.add_subparsers(dest="command")
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("items", nargs="+", help='Add tasks in format: "title" tag1 tag2 ["title2" tag1 ...]. Use || as a delimiter to separate tasks. Alternatively, use "tag" as the first argument to add tags to existing tasks (e.g. add tag <tag> [<tag> ...] <id> [<id> ...]). You may also use "reliance" as the first argument to add task reliance.')
    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("args", nargs="+", help="Delete a task by id, delete a tag from tasks, or delete reliance. For reliance deletion use: delete reliance on <id> (to remove incoming reliance) or delete reliance <id> (to remove a task's own reliance)")
    subparsers.add_parser("delete-all", help="Delete all tasks")
    delete_range_parser = subparsers.add_parser("delete-range", help="Delete tasks in a range")
    delete_range_parser.add_argument("start", type=int, help="Start ID")
    delete_range_parser.add_argument("end", type=int, help="End ID")
    edit_parser = subparsers.add_parser("edit")
    edit_parser.add_argument("id", type=int, nargs="?", help="Task ID (optional)")
    hide_parser = subparsers.add_parser("hide")
    hide_parser.add_argument("id", type=int)
    hide_parser.add_argument("days", type=int)
    args = parser.parse_args()
    task_manager = TaskManager()
    if args.command == "add":
        raw_args = args.items
        if raw_args[0] == "tag":
            if len(raw_args) < 3:
                print("Usage: tasks.py add tag <tag> [<tag> ...] <id> [<id> ...]")
                return
            tags = []
            task_ids = []
            for i, arg in enumerate(raw_args[1:]):
                try:
                    task_ids = list(map(int, raw_args[i+1:]))
                    break
                except ValueError:
                    tags.append(arg)
            if not task_ids:
                print("Task IDs must be integers")
                return
            for tag in tags:
                add_tag_to_tasks(task_manager, tag, task_ids)
        elif raw_args[0] == "reliance":
            tokens = raw_args[1:]
            if tokens and tokens[0] == "time":
                add_time_reliance(task_manager, tokens[1:])
            else:
                add_multiple_reliances(task_manager, tokens)
        else:
            tasks_to_add = []
            current_title = None
            current_tags = []
            for item in raw_args:
                if item == "||":
                    if current_title is not None:
                        tasks_to_add.append((current_title, current_tags))
                        current_title = None
                        current_tags = []
                else:
                    if current_title is None:
                        current_title = item
                    else:
                        current_tags.append(item)
            if current_title is not None:
                tasks_to_add.append((current_title, current_tags))
            add_tasks(task_manager, tasks_to_add)
    elif args.command == "delete":
        if args.args[0] == "tag":
            if len(args.args) < 3:
                print("Usage: tasks.py delete tag <tag> <task id> [<task id> ...]")
                return
            tag = args.args[1]
            try:
                task_ids = list(map(int, args.args[2:]))
            except ValueError:
                print("Task IDs must be integers.")
                return
            delete_tag_from_tasks(task_manager, tag, task_ids)
        elif args.args[0] == "reliance":
            if len(args.args) >= 2 and args.args[1] == "on":
                if len(args.args) != 3:
                    print("Usage: tasks.py delete reliance on <id>")
                    return
                try:
                    dependency_id = int(args.args[2])
                except ValueError:
                    print("Task ID must be an integer.")
                    return
                delete_reliance_on(task_manager, dependency_id)
            else:
                if len(args.args) != 2:
                    print("Usage: tasks.py delete reliance <id>")
                    return
                try:
                    task_id = int(args.args[1])
                except ValueError:
                    print("Task ID must be an integer.")
                    return
                delete_reliance_for(task_manager, task_id)
        else:
            try:
                task_id = int(args.args[0])
            except ValueError:
                print("Task ID must be an integer.")
                return
            delete_task(task_manager, task_id)
    elif args.command == "delete-all":
        delete_all_tasks(task_manager)
    elif args.command == "delete-range":
        delete_range(task_manager, args.start, args.end)
    elif args.command == "edit":
        edit_task(task_manager, args.id)
    elif args.command == "hide":
        hide_task(task_manager, args.id, args.days)
    else:
        list_tasks_by_search(task_manager)

if __name__ == "__main__":
    main()