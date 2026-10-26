class Backpack:
    def __init__(self):
        self.pack = []

    def add_item(self, item):
        flag = False
        if self.count_items_by_type(item.item_type) < 9:
            self.pack.append(item)
            flag = True
        return flag 

    def remove_item_by_type(self, item_type):
        self.pack = [item for item in self.pack if item.item_type != item_type]

    def remove_item(self, item):
        if item in self.pack:
            self.pack.remove(item)

    def get_items(self):
        return self.pack

    def get_items_by_type(self, item_type):
        result = []
        for item in self.pack:
            if item.item_type == item_type:
                result.append(item)
        return result        

    def count_items_by_type(self, item_type):
        count = 0
        for item in self.pack:
            if item.item_type == item_type:
                count+=1
        return count

    def get_item_in_slot(self, item_type, slot):
        '''Предмет типа item_type в слоте slot (1..9) или None'''
        items = self.get_items_by_type(item_type)

        if 1 <= slot <= len(items):
            return items[slot - 1]
        return None
